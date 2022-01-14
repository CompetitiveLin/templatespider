# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main

website = 'bboutique'

class BboutiqueSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://www.bboutique.co']
    # start_urls = ['http://https://www.bboutique.co/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 10
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(BboutiqueSpider, self).__init__(**kwargs)
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
            'https://www.bboutique.co/sex-toys',
            'https://www.bboutique.co/merch',
            'https://www.bboutique.co/sex-toys/top-picks',
            'https://www.bboutique.co/sex-toys/sale',
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

        #url = "http://https://www.bboutique.co/"
        #yield scrapy.Request(
        #    url=url,
        #)

    def parse(self, response):
        url_list = response.xpath("//div[@class='Grid__Style-sc-ju6udt-0 hhjSCS']/div/div/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

        next_page_url = response.xpath("//a[@title='Next page']/@href").get()
        if next_page_url:
           next_page_url = response.urljoin(next_page_url)
           # print("下一页:"+next_page_url)
           yield scrapy.Request(
               url=next_page_url,
               callback=self.parse,
           )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        # price = re.findall("", response.text)[0]
        if True:
            temp = response.xpath('//main/script[@type="application/ld+json"]/text()').get()
            temp_json = json.loads(temp)
            items["brand"] = temp_json['brand']
            items["description"] = ''
            items["name"] = temp_json["name"]
            items["original_price"] = temp_json['offers']["price"]
            items["current_price"] = temp_json['offers']["price"]

            items["source"] = 'bboutique.co'
            images_list = response.xpath('//meta[@name="og:image"]/@content').getall()
            items["images"] = images_list
            #
            Breadcrumb_list = ['Home']+response.xpath("//div[@class='Structure-sc-122ascm-0 kCFULE']/a/text()").getall()+[items["name"]]
            for b in range(len(Breadcrumb_list)):
                Breadcrumb_list[b] = Breadcrumb_list[b].replace('\r','').replace('\n','').replace('\t','').strip(' ').replace('\xa0','')
            items["cat"] = Breadcrumb_list[-1]
            items["detail_cat"] = '/'.join(Breadcrumb_list)
            #
            sku_list = list()
            colors = response.xpath("(//div[@class='Space-sc-1ykp986-0 hMmFAN']//div[@class='MediaQuery__Query-sc-dh9ch6-0 duMCMM'])[last()]//input/@name").getall()
            for sku in colors:
                sku_item = SkuItem()
                sku_item["original_price"] = items["original_price"]
                sku_item["current_price"] = items["current_price"]
                attributes = SkuAttributesItem()
                if re.findall(r'([0-9]+)',sku) and re.findall(r'([0-9]+)',sku)[0]  == sku:
                    attributes["size"] = sku
                    sku_item["original_price"] = '$'+str(sku)
                    sku_item["current_price"] = '$'+str(sku)
                else:
                    attributes["colour"] = sku
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)

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

            print(items)
            # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
            #                skulist_attributes=True)
            # yield items
