# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

from lxml import etree
import math
from  overseaSpider.util import item_check

website = 'doughstore'

class DoughstoreSpider(scrapy.Spider):
    name = website
    allowed_domains = ['doughstore.com']
    start_urls = ['http://doughstore.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(DoughstoreSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "涛儿")

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

    def filter_html_label(self, text):
        html_labels = re.findall(r'<[^>]+>', text)
        for h in html_labels:
            text = text.replace(h, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').replace('\xa0', '').strip()
        return text

    def start_requests(self):
        urls = ['https://doughstore.com/collections/shoes','https://doughstore.com/collections/clothing','https://doughstore.com/collections/accessories']
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )


    def parse_list(self, response):
        """列表页"""

        url_list = response.xpath('//a[@class="full-unstyled-link"]/@href').getall()
        url_list = ['https://doughstore.com' + url for url in url_list]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

        next_url = response.xpath('//a[@aria-label="Next page"]/@href').get()
        if next_url:
            yield scrapy.Request(
                url='https://doughstore.com' + next_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        """详情页"""

        check_sold_out_1 = 'self.filter_html_label(check_sold_out)'
        if 'Sold Out' != check_sold_out_1:
            items = ShopItem()
            items["url"] = response.url
            items["source"] = 'doughstore.com'

            name = response.xpath('//h1[@class="product__title"]/text()').get()
            if name:
                items["name"] = self.filter_html_label(name)

            current_price = response.xpath('//option[@selected="selected"]/text()').get().split('$')[-1]

            if current_price:
                items["current_price"] = self.filter_html_label(current_price)
                items["original_price"] = items["current_price"]

            description = []
            if description:
                items["description"] = description

            images_list = response.xpath('//div[@class="product__media media"]/img/@src').getall()
            images_list = ['https:' + img for img in images_list]
            items["images"] = images_list
            items["cat"] = items["name"]
            items["detail_cat"] = 'Home/' + items["name"]
            # Breadcrumb_list = response.xpath('').getall()
            # meta = response.meta
            # detal_cat = meta['cat']
            #
            # items["cat"] = items["name"]
            # detail_cat = 'Home' + '/' + detal_cat + '/'+ items["cat"]
            # items["detail_cat"] = detail_cat
            size_list = []
            get_size = response.xpath('//div[@class="variant-wrapper variant-wrapper-- js"]//fieldset/div//label')
            for i in get_size:
                check = i.xpath('.//@class').get()
                if not check:
                    size_1 = i.xpath('.//text()').get()
                    size_list.append(size_1)


            sku_list = list()
            for size in size_list:
                '''SkuAttributesItem'''
                SAI = SkuAttributesItem()
                SAI['size'] = size
                SI = SkuItem()
                SI['attributes'] = SAI
                SI['imgs'] = items['images']
                SI['url'] = items['url']
                SI['original_price'] = items['original_price']
                SI['current_price'] = items['current_price']
                sku_list.append(SI)

            items["sku_list"] = []
            try:
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
                # print('=============')
                # print(items)
                yield items
            except:
                pass

