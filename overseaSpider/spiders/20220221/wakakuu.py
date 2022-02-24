# -*- coding: utf-8 -*-
import html
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.item_check import check_item
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main

website = 'wakakuu'

class WakakuuSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://www.wakakuu.com/']
    # start_urls = ['http://https://www.wakakuu.com//']

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
        super(WakakuuSpider, self).__init__(**kwargs)
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
            'https://www.wakakuu.com/se/nyheter',
            'https://www.wakakuu.com/se/dam/klader',
            'https://www.wakakuu.com/se/dam/vaskor',
            'https://www.wakakuu.com/se/dam/skor',
            'https://www.wakakuu.com/se/dam/accessoarer',
            'https://www.wakakuu.com/se/dam/lifestyle',
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

    def parse(self, response):

        url_list = response.xpath('//a[@class="product__image-link"]/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
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
        # price = re.findall("", response.text)[0]
        original_price = response.xpath('//div[@class="product-detail__price"]/text()').get()
        items["original_price"] = original_price.replace(' ', '').replace('SEK', '').strip()
        items["current_price"] = items["original_price"]
        items["brand"] = response.xpath('//span[@itemprop="brand"]/text()').get().replace('\r','').replace('\n','').replace('\t','').strip(' ')
        items["name"] = response.xpath('//h1[@class="product-detail__name"]/a/text()').get().replace('\r','').replace('\n','').replace('\t','').strip(' ')
        # attributes = list()
        # items["attributes"] = attributes
        # items["about"] = response.xpath("").get()
        description = response.xpath('//div[@id="description"]/text()').getall()
        items["description"] = self.filter_html_label(''.join(description))
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        items["source"] = website
        images_list = response.xpath('//div[@id="product-page-image-slider"]/img/@src').getall()
        images_list = [response.urljoin(url) for url in images_list]
        items["images"] = images_list
        #
        cat_list = ['Home', items["name"]]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        sizes = response.xpath("//div[@class='sizes']/select/option[not(@disabled)]/text()").getall()
        sku_list = list()
        for sku in sizes:
            sku_item = SkuItem()
            sku_item["original_price"] = items["original_price"]
            sku_item["current_price"] = items["current_price"]
            attributes = SkuAttributesItem()
            attributes["size"] = sku.replace('\r','').replace('\n','').replace('\t','').strip(' ')
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

        # check_item(items)
        # print(items)
        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                skulist_attributes=True)
        yield items

    def filter_html_label(self, text):
        text = str(text)
        text = html.unescape(text)
        # 注释，js，css，html标签
        filter_rerule_list = [r'(<!--[\s\S]*?-->)', r'<script[\s\S]*?</script>', r'<style[\s\S]*?</style>', r'<[^>]+>']
        for filter_rerule in filter_rerule_list:
            html_labels = re.findall(filter_rerule, text)
            for h in html_labels:
                text = text.replace(h, ' ')
        filter_char_list = [
            u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000', u'\u200a', u'\u2028', u'\u2029', u'\u202f', u'\u205f',
            u'\u3000', u'\xA0', u'\u180E', u'\u200A', u'\u202F', u'\u205F', '\t', '\n', '\r', '\f', '\v',
        ]
        for f_char in filter_char_list:
            text = text.replace(f_char, '')
        text = re.sub(' +', ' ', text).strip()
        return text