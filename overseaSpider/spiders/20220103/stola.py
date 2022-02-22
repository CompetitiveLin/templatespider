# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import demjson
import requests
from hashlib import md5
from scrapy.selector import Selector

from overseaSpider.util.utils import isLinux, filter_text
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'stola'

class StolaSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['stola.jp']
    # start_urls = ['http://stola.jp/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(StolaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "凯棋")

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
            #'overseaSpider.middlewares.AiohttpMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
        'DOWNLOAD_HANDLERS': {
            "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
            # "https": "overseaSpider.downloadhandlers.Ja3DownloadHandler",
            # 'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler',

        },
    }

    def start_requests(self):
        url_list = [
            "https://stola.jp/itemlist?cateid=1",
            "https://stola.jp/itemlist?cateid=2",
            "https://stola.jp/itemlist?cateid=3",
            "https://stola.jp/itemlist?cateid=4",
            "https://stola.jp/itemlist?cateid=5",
        ]
        for url in url_list:
            print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,

            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//article[@id='products_list']//ul[@class='item-list1 item-list-sp1']/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        if url_list:
            for url in url_list:
                print(url)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                )

            next_page_url = response.xpath("//a[@class='next']/@href").get()
            if next_page_url:
               next_page_url = response.urljoin(next_page_url)
               print("下一页:"+next_page_url)
               yield scrapy.Request(
                   url=next_page_url,
                   callback=self.parse_list,
               )

    def parse_detail(self, response):
        """详情页"""
        # res = requests.get(sku_url)
        # sku_res = Selector(text=res.text)
        name = response.xpath("//meta[@property='og:title']/@content").get()
        # description = response.xpath("//meta[@property='og:description']/@content").get()
        # image = response.xpath("//meta[@property='og:image']/@content").get()
        # price = response.xpath("//meta[@property='product:price:amount']/@content").get()
        # brand = response.xpath("//meta[@property='product:brand']/@content").get()

        items = ShopItem()
        items["url"] = response.url
        #json_str = response.xpath('//script[@type="application/ld+json"]/text()').get()
        #json_data = json.loads(json_str)
        #brand = json_data["brand"]["name"]
        #price = json_data["offers"]["price"]
        #description = json_data["description"]
        # re.findall("", response.text)[0]
        original_price = response.xpath("//div[@class='price_box']/p/text()").get().replace("¥", "").replace(",", "")
        current_price = response.xpath("//div[@class='price_box']/p/text()").get().replace("¥", "").replace(",", "")
        items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
        items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
        items["brand"] = ''
        items["name"] = name
        description = response.xpath("//div[@class='detail_text']/p/text()").getall()
        items["description"] = "".join(description)
        items["source"] = website
        images_list = response.xpath("//div[@class='slide']//ul[@class='move clearfix']/li//img/@src").getall()
        images_list_new = list()
        for i in images_list:
            img_list = i.split("/")
            img_list.insert(-1, "original")
            img = "/".join(img_list)
            images_list_new.append(img)

        # images_list = ["/".join(i.split("/").insert(-1, "original")) for i in images_list]

        items["images"] = images_list_new

        Breadcrumb_list = response.xpath("//ol[@id='topicpath']/li/a/text()").getall()
        items["cat"] = Breadcrumb_list[-1]
        items["detail_cat"] = "/".join(Breadcrumb_list)


        # attributes_list = list()
        # tr_list = response.xpath("")
        # for tr in tr_list:
        #     k = tr.xpath("./th/text()").get()
        #     v_list = tr.xpath("./td/text()").getall()
        #     v = "".join(v_list)
        #     attributes = k+""+v
        #     attributes_list.append(attributes)
        # items["attributes"] = attributes_list

        # items["about"] = response.xpath("").get()
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()

        sku_list = list()

        size_list = response.xpath("//div[@class='color_list']//div[@class='color_stock']//ul/li/text()").getall()
        color_list = response.xpath("//div[@class='color_list']//div[@class='color_stock']//p/text()").getall()
        size_list = list(set(size_list)) if size_list else size_list

        if size_list:
            for size in size_list:
                if color_list:
                    for color in color_list:
                        sku_item = SkuItem()
                        sku_item["original_price"] = items["original_price"]
                        sku_item["current_price"] = items["current_price"]
                        attributes = SkuAttributesItem()
                        attributes["colour"] = color
                        attributes["size"] = size
                        other = dict()
                        attributes["other"] = other
                        sku_item["attributes"] = attributes
                        sku_list.append(sku_item)
                else:
                    sku_item = SkuItem()
                    sku_item["original_price"] = items["original_price"]
                    sku_item["current_price"] = items["current_price"]
                    attributes = SkuAttributesItem()
                    attributes["size"] = size
                    other = dict()
                    attributes["other"] = other
                    sku_item["attributes"] = attributes
                    sku_list.append(sku_item)
        else:
            if color_list:
                for color in color_list:
                    sku_item = SkuItem()
                    sku_item["original_price"] = items["original_price"]
                    sku_item["current_price"] = items["current_price"]
                    attributes = SkuAttributesItem()
                    attributes["colour"] = color
                    other = dict()
                    attributes["other"] = other
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
        # yield items
