# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util import item_check
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'inkbox'

class InkboxSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['inkbox.com']
    # start_urls = ['http://inkbox.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 10
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(InkboxSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "汀幡")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }
    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text
    def start_requests(self):
        url_list = [
            'https://inkbox.com/products/all-tattoos?page=1'
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

        #url = "http://inkbox.com/"
        #yield scrapy.Request(
        #    url=url,
        #)

    def parse(self, response):
        url_list = response.xpath('//div[@class="relative group"]/a/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        if url_list:
            if '?page=' not in response.url:
                url1 = response.url+'?page=1'
                prefix = url1.split('page=')[0]
                surfix = url1.split('page=')[1]
                surfix = int(surfix) + 1
                next_page_url = prefix + 'page=' + str(surfix)
                if next_page_url:
                    # print("下一页:" + next_page_url)
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse,
                    )
            else:
                prefix = response.url.split('page=')[0]
                surfix = response.url.split('page=')[1]
                surfix = int(surfix) + 1
                next_page_url = prefix + 'page=' + str(surfix)
                if next_page_url:
                    # print("下一页:" + next_page_url)
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse,
                    )
    # def parse_list(self, response):
    #     """列表页"""
    #     url_list = response.xpath("").getall()
    #     url_list = [response.urljoin(url) for url in url_list]
    #     for url in url_list:
    #         print(url)
    #         yield scrapy.Request(
    #             url=url,
    #             callback=self.parse_detail,
    #         )

        # response_url = parse.unquote(response.url)
        # split_str = ''
        # base_url = response_url.split(split_str)[0]
        # page_num = int(response_url.split(split_str)[1])+1
        # next_page_url = base_url + split_str + str(page_num)
        #next_page_url = response.xpath("").get()
        #if next_page_url:
        #   next_page_url = response.urljoin(next_page_url)
        #    print("下一页:"+next_page_url)
        #    yield scrapy.Request(
        #        url=next_page_url,
        #        callback=self.parse_list,
        #    )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        # price = re.findall("", response.text)[0]
        original_price = response.xpath('//div[@class="pt-6 flex flex-col"]/div[@class="text-sm md:text-base"]/span/text()').get()
        current_price = ''
        if original_price:
            original_price =self.filter_text(original_price)
            current_price = response.xpath('//div[@class="pt-6 flex flex-col"]/div[@class="font-bold font-body md:text-lg  text-brand-red "]/text()').get()
            current_price =self.filter_text(current_price)
        else:
            current_price = response.xpath('//div[@class="font-bold font-body md:text-lg "]/text()').get()
            current_price = self.filter_text(current_price)
            original_price = current_price
        items["original_price"] = original_price
        items["current_price"] = current_price
        brand = response.xpath('//p[@class="text-sm xl:text-base"]/a/text()').get()
        if brand:
            brand = self.filter_text(brand)
        else:
            brand = website
        items["brand"] = brand
        name = response.xpath('//div[@class="flex justify-between items-center"]/h3/text()').get()
        name = self.filter_text(name)
        items["name"] = name
        # attributes = list()
        # items["attributes"] = attributes
        # items["about"] = response.xpath("").get()
        des = response.xpath('//div[@class="pt-7 text-sm font-body leading-6"]//text()').getall()
        description = ''
        for i in des:
            a = self.filter_text(i)
            if a != '':
                description += a
        items["description"] = description
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        items["source"] = website
        images_list1 = response.xpath('//div[@class="flex w-max-content h-16 md:h-20 xl:h-24 space-x-4 relative"]/div/img/@src').getall()
        images_list = []
        for i in images_list1:
            if 'inkboxdesigns.imgix.net/product/packaging/default.jpg?auto=compress,format' not in i:
                a = 'https:'+i
                images_list.append(a)
        items["images"] = images_list

        items["cat"] = ''
        items["detail_cat"] = ''

        sku_list = list()
        #for sku in original_sku_list:
        #     sku_item = SkuItem()
        #     sku_item["original_price"] = item["original_price"]
        #     sku_item["current_price"] = item["current_price"]
        #     sku_item["inventory"] = sku["inventory"]
        #     sku_item["sku"] = sku["sku"]
        #     imgs = list()
        #     sku_item["imgs"] = imgs
        #     sku_item["url"] = response.url
        #     sku_item["sku"] = sku
        #     attributes = SkuAttributesItem()
        #     attributes["colour"] = sku["name"]
        #     attributes["size"] = sku["size"]
        #     other = dict()
        #     attributes["other"] = other
        #     sku_item["attributes"] = attributes
        #     sku_list.append(sku_item)

        items["sku_list"] = sku_list
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
        #     num=self.settings["CLOSESPIDER_ITEMCOUNT"],
        #     skulist=True,
        #     skulist_attributes=True)
        print(items)
        # item_check.check_item(items)
        # yield items

