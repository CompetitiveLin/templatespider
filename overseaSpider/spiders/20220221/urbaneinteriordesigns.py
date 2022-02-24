import scrapy
import re
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
import time
import base64
import random
from hashlib import md5
import requests
from lxml import etree
import math
import html
import json
import httpx
import demjson
from scrapy.selector import Selector

from overseaSpider.util.item_check import check_item
from overseaSpider.util.utils import isLinux

url_list = []
author = '泽塔'
website = 'urbaneinteriordesigns'
domainname = 'https://urbaneinteriordesigns.com'
target_urls = [
    "https://urbaneinteriordesigns.com/shop-4/",
]


class UrbaneinteriordesignsSpider(scrapy.Spider):
    name = website

    # 域名

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(UrbaneinteriordesignsSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', author)

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ALWAYS_STORE': False,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60,  # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware_Domestic': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
        'DOWNLOAD_HANDLERS': {
            # "https": "overseaSpider.downloadhandlers.Ja3DownloadHandler",
            # "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
            # 'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler',
        }
    }

    # 去掉价格符号
    def filter_money_label(self, text):
        text = text.replace('$', '').strip()
        return text

    # 不改变顺序去重(list)
    def delete_duplicate(self, oldlist):
        newlist = list(set(oldlist))
        newlist.sort(key=oldlist.index)
        return newlist

    # 过滤html标签
    def filter_html_label(self, text, type):
        text = str(text)
        html_labels_zhushi = re.findall('(<!--[\s\S]*?-->)', text)  # 注释
        if html_labels_zhushi:
            for zhushi in html_labels_zhushi:
                text = text.replace(zhushi, ' ')
        html_labels = re.findall(r'<[^>]+>', text)  # html标签
        if type == 1:
            for h in html_labels:
                text = text.replace(h, ' ')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('&gt;', '').replace('&amp;',
                                                                                                      '&').replace(
            '\xa0', '').replace('&lt;', '').replace('  ', '').strip()
        return text

    def start_requests(self):
        # 目标url
        urls = target_urls
        for url in urls:
            if url not in url_list:
                url_list.append(url)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_list,
                )


    def parse_list(self, response):
        parse_detail_url = response.xpath('//ul[@class="products columns-3"]/li/a[1]/@href').getall()
        if parse_detail_url:
            parse_detail_url = [p for p in list(set(parse_detail_url)) if
                                str(p).strip() != '' and str(p).strip() != '#' and 'javascript:' not in str(p).strip()]
            for detail_url in parse_detail_url:
                if domainname not in detail_url:
                    detail_url = domainname + detail_url
                if detail_url not in url_list:
                    url_list.append(detail_url)
                    yield scrapy.Request(
                        url=detail_url,
                        callback=self.parse_detail,
                    )
        next_page_url = response.xpath('//a[@class="next page-numbers"]/@href').get()
        if next_page_url:
            if str(next_page_url).strip() != '' and str(next_page_url).strip() != '#' and 'javascript:' not in str(
                    next_page_url).strip():
                if domainname not in next_page_url:
                    next_page_url = domainname + next_page_url
                if next_page_url not in url_list:
                    url_list.append(next_page_url)
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse_list,
                    )

    def parse_detail(self, response):
        items = ShopItem()

        # source-名称
        items['source'] = website

        # url-目标url
        items['url'] = response.url

        # name-商品名称
        name_text = response.xpath('//h1[@class="product_title entry-title"]').get()
        if name_text:
            name_text = self.filter_html_label(name_text, 1)
            items['name'] = name_text.strip()
        items['brand'] = ''
        # cat-最后一级目录

        items['cat'] = items['name']

        # detail_cat-全部目录
        items['detail_cat'] = "Home/" + items['cat']

        # attributes-商品属性材质列表（list）
        attributes_list = list()
        att_list = response.xpath('//div[@class="woocommerce-product-details__short-description"]//p').getall()
        if att_list:
            for attl in att_list:
                attl_text = self.filter_html_label(attl, 1)
                attributes_list.append(attl_text)
        if attributes_list:
            items['attributes'] = attributes_list

        # measurements-规格尺寸
        items['measurements'] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

        # original_price-原价
        # current_price-现价
        m1 = ''
        m2 = ''
        money = response.xpath(
            '//div[@class="summary entry-summary"]//span[@class="woocommerce-Price-amount amount"]').get()
        if money:
            money = self.filter_html_label(money, 1)
            money = self.filter_money_label(str(money))
            items['current_price'] = money
            items['original_price'] = money
            m1 = money
            m2 = money
            # new_original_price = response.xpath('&&&').get()
            # if new_original_price:
            #     new_original_price = self.filter_html_label(new_original_price, 1)
            #     new_original_price = self.filter_money_label(str(new_original_price))
            #     items['original_price'] = new_original_price
            #     m2 = new_original_price

        # description-商品功能描述
        description_text = response.xpath('//div[@id="tab-description"]').get()
        if description_text:
            description_text = self.filter_html_label(description_text, 1)
            items['description'] = description_text

        # images-图片list
        img_list = response.xpath('//figure[@class="woocommerce-product-gallery__wrapper"]//a/@href').getall()
        if img_list:
            items['images'] = self.delete_duplicate(img_list)

        # sku_list-存在有不用颜色块和不同尺寸的时候使用（list）
        items["sku_list"] = list()
        my_sku_list = []
        itemsa = SkuItem()
        itemsb = SkuAttributesItem()


        # 以下为lastCrawlTime,created，updated，is_deleted的固定写法
        try:
            status_list = list()
            status_list.append(items["source"])
            status_list.append(items["name"])
            status_list.append(items["original_price"])
            status_list.append(items["current_price"])
            status_list = [i for i in status_list if i]
            status = "-".join(status_list)
            items["id"] = md5(status.encode("utf8")).hexdigest()
            items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            items["created"] = int(time.time())
            items["updated"] = int(time.time())
            items['is_deleted'] = 0
            # print("==================")
            # check_item(items)
            # print(items)
            yield items
        except:
            pass
