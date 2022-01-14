# -*- coding: utf-8 -*-
import re
import time
import json

import demjson
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
from overseaSpider.util.item_check import check_item
from lxml import etree
import demjson
from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem

website = 'surlatable'

class SurlatableSpider(scrapy.Spider):
    name = website
    # start_urls = ['https://www.surlatable.com/']


    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(SurlatableSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "泽塔")


    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },

    }

    def filter_html_label(self, text, type):
        html_labels_zhushi = re.findall('(<!--[\s\S]*?-->)', text)  # 注释
        if html_labels_zhushi:
            for zhushi in html_labels_zhushi:
                text = text.replace(zhushi, '')
        html_labels = re.findall(r'<[^>]+>', text)  # html标签
        if type == 1:
            for h in html_labels:
                text = text.replace(h, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

    def filter_text(self,input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def start_requests(self):
        url = "https://www.surlatable.com/"
        yield scrapy.Request(
            url=url,
            # headers=self.headers
        )

    def parse(self, response):
        """主页"""
        url_list = ["https://www.surlatable.com/products/cookware/",
                    "https://www.surlatable.com/products/bakeware/",
                    "https://www.surlatable.com/products/kitchen-tools/",
                    "https://www.surlatable.com/products/knives/",
                    "https://www.surlatable.com/products/small-appliances/",
                    "https://www.surlatable.com/products/dining-home/",
                    "https://www.surlatable.com/products/coffee-tea/",
                    "https://www.surlatable.com/products/food/",
                    "https://www.surlatable.com/products/outdoor/"
                    ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                # headers=self.headers
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='product-tile']//a[@class='thumb-link']/@href").getall()
        # detail_url_list = [response.urljoin(url) for url in detail_url_list]
        if detail_url_list:
            # print(f"当前商品列表页有{len(detail_url_list)}条数据")
            for detail_url in detail_url_list:
                detail_url = response.urljoin(detail_url)
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    # headers=self.headers
                )

            next_page_url = response.xpath("//a[@class='page-next']/@href").get()
            if next_page_url:
                # next_page_url = response.urljoin(next_page_url)
                print("下一页:"+next_page_url)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_list,
                    # headers=self.headers
                )
        else:
            print(f"商品列表页无数据!:{response.url}")

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        # INCLUDE SKU INFO:
        html_json_data = response.xpath("//script[@type='application/ld+json' and contains(text(), 'color')]/text()").get()
        html_json_data = html_json_data.replace('\n', '')
        json_data = re.search('(.*?)}}{', html_json_data, flags=re.S).group(1) + '}}'
        json_data = '{"INFO":[' + json_data + ']}'
        json_data = demjson.decode(json_data)

        detail_cat_list = response.xpath("//div[@class='breadcrumb']//a/text()").getall()
        detail_cat = str(detail_cat_list).replace("[", "").replace("]", "").replace(", ", "/").replace("'", "").replace(" /", "/")
        cat = detail_cat.split("/")[-1]
        description = response.xpath("//div[@class='main-description']/div[@class='description left-section']").get()
        current_price = "$" + json_data["INFO"][0]["offers"]["Price"]
        original_price = response.xpath("//div[@class='suggested-price cross-price']/span[@class='price']/text()").get()
        items["current_price"] = current_price
        if original_price:
            items["original_price"] = original_price
        else:
            items["original_price"] = items["current_price"]
        items["brand"] = json_data["INFO"][0]["brand"]["name"]
        items["name"] = response.xpath("//div[@id='pdpMain']//h1[@class='product-name']/text()").get()
        items["detail_cat"] = detail_cat
        items["cat"] = cat
        # images_list = list()
        images_list = json_data["INFO"][0]["image"]
        items["images"] = images_list
        items["url"] = response.url
        items["source"] = website
        items["description"] = self.filter_html_label(str(description), 1)
        items["sku_list"] = list()
        my_sku_list = list()
        if not json_data["INFO"][0]["color"] == "":
            sku_list = json_data["INFO"]
            for sku in sku_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                sku_info["sku"] = sku["sku"]
                sku_attr["colour"] = sku["color"]
                sku_info["imgs"] = sku["image"]
                sku_info["current_price"] = "$" + json_data["INFO"][0]["offers"]["Price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["attributes"] = sku_attr
                my_sku_list.append(sku_info)
        if my_sku_list != []:
            items["sku_list"] = my_sku_list

        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
        status_list = list()
        status_list.append(items["url"])
        status_list.append(items["original_price"])
        status_list.append(items["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        items["id"] = md5(status.encode("utf8")).hexdigest()

        items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        items["created"] = int(time.time())
        items["updated"] = int(time.time())
        items['is_deleted'] = 0
        print(items)
        # yield items
        # check_item(items)


