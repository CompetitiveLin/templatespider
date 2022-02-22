# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from lxml import etree
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main

website = 'lyleandscott'

class LyleandscottSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://www.lyleandscott.com/']
    # start_urls = ['http://https://www.lyleandscott.com//']
    urls = 'https://www.lyleandscott.com'

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings['CLOSESPIDER_ITEMCOUNT'] = 20
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(LyleandscottSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "肥鹅")

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

    def start_requests(self):
        url_list = [
            'https://row.lyleandscott.com/sale.list',
            'https://row.lyleandscott.com/new-arrivals.list',
            'https://row.lyleandscott.com/mens.list',
            'https://row.lyleandscott.com/womens.list',
            'https://row.lyleandscott.com/kidswear/view-all.list',
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

        #url = "http://https://www.lyleandscott.com//"
        #yield scrapy.Request(
        #    url=url,
        #)

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


    def parse(self, response):
        url_list = response.xpath('//a[@class="productBlock_link"]/@href').getall()
        url_list = [self.urls + url for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        price = self.price_fliter(response.xpath('//p[@class="productPrice_price "]/text()').get())[1:]
        original_price = price
        current_price = price
        items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
        items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
        items["brand"] = response.xpath('//div[@data-information-component="brand"]/div/text()').get()
        name = response.xpath('//h1[@class="productName_title"]/text()').get()
        items["name"] = name
        # attributes = list()
        # attribute = response.xpath("//div[@class='tab details']/div//text()").getall()
        # for a in attribute:
        #     a = a.replace('\n','').replace('\r','').replace('\t','')
        #     if a:
        #         attributes.append(a)
        # items["attributes"] = attributes
        care = response.xpath("//div[@class='tab material']/div//text()").getall()
        cares = ''
        for c in care:
            c = c.replace('\n', '').replace('\r', '').replace('\t', '').strip(' ')
            if c:
                cares = cares + c
        items["care"] = cares
        items["source"] = website
        images_list = response.xpath('//img[@class="athenaProductImageCarousel_imagePreview"]/@src').getall()
        items["images"] = images_list
        items["cat"] = name
        items["detail_cat"] = "Home/" + name
        items["sku_list"] = []
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
        status_list = list()
        status_list.append(items["url"])
        status_list.append(items["original_price"])
        status_list.append(items["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        items["id"] = md5(status.encode("utf8")).hexdigest()
        #
        items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        items["created"] = int(time.time())
        items["updated"] = int(time.time())
        items['is_deleted'] = 0

        # print(items)
        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                 skulist_attributes=True)
        yield items

    def get_sku(self,url):
        session = requests.session()
        response = session.get(url)
        response = etree.HTML(response.text)
        original_price = ''
        current_price = ''
        images_list = list()
        original_price = response.xpath("//span[@class='price-standard']/text()")
        if original_price:
            original_price = original_price[0]
        current_price = response.xpath("//span[@class='price-sales']/text()")
        if current_price:
            current_price = current_price[0]
        images_list = response.xpath("//div[@id='thumbnails']/ul/li/a/@href")
        original_price = "" + str(original_price) if original_price else "" + str(current_price)
        current_price = "" + str(current_price) if current_price else "" + str(original_price)
        information = {
            'original_price_sku':original_price,
            'current_price_sku':current_price,
            'images_list_sku':images_list
        }
        return information




