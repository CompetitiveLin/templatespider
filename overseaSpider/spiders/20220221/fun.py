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


website = 'fun'

class FunSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://www.fun.com/']
    # start_urls = ['http://https://www.fun.com//']

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
        super(FunSpider, self).__init__(**kwargs)
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
            'https://www.fun.com/movie-themed-gifts.html?page=1',
            'https://www.fun.com/television-themed-gifts.html?page=1',
            'https://www.fun.com/gifts.html?page=1',
            'https://www.fun.com/gifts-for-men.html?page=1',
            'https://www.fun.com/gifts-for-women.html?page=1',
            'https://www.fun.com/gifts-for-kids.html?page=1',
            'https://www.fun.com/interests.html?page=1',
            'https://www.fun.com/exclusives.html?page=1',
            'https://www.fun.com/sale.html?page=1'
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

        #url = "http://https://www.fun.com//"
        #yield scrapy.Request(
        #    url=url,
        #)

    def parse(self, response):
        url_list = response.xpath('//h2[@class="card-title"]/a/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

        if url_list:
            next = response.url.split('?page=')[0] + '?page=' + str(int(response.url.split('?page=')[1]) + 1)
            # print('下一页 '+next)
            yield scrapy.Request(
                url=next,
                callback=self.parse,
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        original_price = response.xpath("//div[@class='purchase__price my-3']/span[@class='price price--strike']/text()").get()
        current_price = response.xpath("//div[@class='purchase__price my-3']/span[@class='price price--sale']/text()").get()
        if not original_price and not current_price:
            original_price = current_price = response.xpath("//div[@class='purchase__price my-3']/span/text()").get()
        items["original_price"] = self.price_fliter("" + str(original_price) if original_price else "" + str(current_price))
        items["current_price"] = self.price_fliter("" + str(current_price) if current_price else "" + str(original_price))
        items["name"] = response.xpath("//div[@class='card-body']/h1/text()").get()
        attributes = list()
        attribute = response.xpath("//div[@id='includes']//text()").getall()
        for a in attribute:
            a = a.replace('\r','').replace('\n','').replace('\t','').replace('\xa0','').strip()
            if a:
                attributes.append(a)
        items["attributes"] = attributes
        descriptions = response.xpath("//div[@id='prodDesc']//text()").getall()
        description = ''
        for d in descriptions:
            d = d.replace('\r',' ').replace('\n',' ').replace('\t',' ').replace('\xa0',' ')
            if d:
                description = description + d
        items["description"] = description
        items["source"] = website
        images_list = response.xpath("//div[@class='gal__scroll']/a/@href").getall()
        if not images_list:
            images_list = response.xpath("//div[@class='col text-center mb-4 prdImg ']/a/img/@src").getall()
        items["images"] = images_list
        Breadcrumb_list = response.xpath("//div[@id='bcr']//li//a//span/text()").getall()
        detail_cat = ''
        for b in Breadcrumb_list:
            b = b.replace('\r','').replace('\n','').replace('\t','').strip()
            if b and b!='More From This Category:':
                detail_cat = detail_cat  + b + '/'
        items["detail_cat"] = detail_cat[:-1]
        items["cat"] = items["detail_cat"].split('/')[-1]
        #
        sku_list = list()
        for sku in response.xpath("//div[@id='pnlSizes']//label[contains(@class,'dropdown-item')]/span"):
            size = sku.xpath("./text()[1]").get().replace('\r','').replace('\n','').replace('\t','').replace('\xa0','').strip()
            price = sku.xpath("./span/text()").get().replace('\r','').replace('\n','').replace('\t','').replace('\xa0','').strip()
            sku_item = SkuItem()
            sku_item["original_price"] = self.price_fliter(price)
            sku_item["current_price"] = self.price_fliter(price)
            sku_item["imgs"] = images_list
            attributes = SkuAttributesItem()
            attributes["size"] = size
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

        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                skulist_attributes=True)
        # print(items)
        yield items


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