# -*- coding: utf-8 -*-
import re
import time
import json
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
from overseaSpider.util.item_check import check_item
from lxml import etree
from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem
from overseaSpider.util.scriptdetection import detection_main

website = 'furtherfood'

class OverseaSpider(scrapy.Spider):
    name = website
    # start_urls = ['https://www.furtherfood.com/']


    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUN"] = 10
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(OverseaSpider, self).__init__(**kwargs)
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

    def price_fliter(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ', '$', '€', ',', '\n',
                       '¥']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def start_requests(self):
        url = "https://www.furtherfood.com/"
        yield scrapy.Request(
            url=url,
            # headers=self.headers
        )

    def parse(self, response):
        """主页"""
        url_list = ["https://shop.furtherfood.com/collections/all-products"
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
        detail_url_list = response.xpath("//h2[@class='product-item__title']/a/@href").getall()
        detail_url_list = [response.urljoin(url) for url in detail_url_list]
        if detail_url_list:
            # print(f"当前商品列表页有{len(detail_url_list)}条数据")
            for detail_url in detail_url_list:
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    # headers=self.headers
                )
        else:
            print(f"商品列表页无数据!:{response.url}")

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        # [JUDGE IF SOLD OUT]
        # [NOT NEEDING]
        # [CATEGORY]
        detail_cat_list = response.xpath("//nav[@class='breadcrumb']//li//span/text()").getall()
        detail_cat_list = [detail.replace("\n", "").strip() for detail in detail_cat_list]
        detail_cat = str(detail_cat_list).replace("[", "").replace("]", "").replace("'", "").replace('"', '').replace(", ", "/")
        cat = detail_cat.split("/")[-1]
        # [SALE PRICE]
        original_price = response.xpath("//div[@class='product-meta  product-meta--desktop']//span[@class='product-meta__price product-meta__price--old']/span/text()").get()
        current_price = response.xpath("//div[@class='product-meta  product-meta--desktop']//span[@class='product-meta__price product-meta__price--new']/span/text()").get()
        if original_price:
            items["current_price"] = self.price_fliter(current_price.strip())
            items["original_price"] = self.price_fliter(original_price.strip())
        # [NORMAL PRICE]
        else:
            current_price = response.xpath("//div[@class='product-meta  product-meta--desktop']//span[@class='product-meta__price']/span/text()").get()
            items["current_price"] = self.price_fliter(current_price.strip())
            items["original_price"] = items["current_price"]
        # [OTHER ITEMS]
        brand = "Further Food"
        items["brand"] = brand.replace("\n", "").replace("\u3000", " ").strip()
        name = response.xpath("//div[@class='product-meta  product-meta--desktop']//h1[@class='product-meta__title']/text()").get()
        items["name"] = name.replace("\n", "").replace("\u3000", " ").strip()
        items["detail_cat"] = detail_cat
        items["cat"] = cat
        # [IMAGES INFO]
        images_list_info = response.xpath('//ul[@class="product__slideshow"]//@data-image-large-url').getall()
        images_list = ["https:" + img_url for img_url in images_list_info]
        items["images"] = images_list
        items["url"] = response.url
        items["source"] = website
        description = response.xpath("//meta[@name='description']/@content").get()
        description = self.filter_html_label(str(description), 1)
        items["description"] = self.filter_text(description)
        items["sku_list"] = list()
        # [SKU INFO]
        my_sku_list = list()
        # [SKU COLOR-NO DATA]
        # [SKU IMG-NO DATA]
        # [SKU OTHER-NO DATA]
        # [SKU SIZE]
        sku_size_list = response.xpath("//select[@class='single-option-selector']/option/text()").getall()
        if sku_size_list:
            sku_size_list = [size.replace("\n", "").strip() for size in sku_size_list]
        # [SKU GARBAGE]
        if sku_size_list:
            for size in sku_size_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()

                sku_attr["size"] = size
                sku_info["current_price"] = items["current_price"]
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

        # detection_main(
        #     items=items,
        #     website=website,
        #     num=10,
        #     skulist=True,
        #     skulist_attributes=True
        # )
        # print(items)
        yield items
        # check_item(items)


