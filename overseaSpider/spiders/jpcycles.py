# -*- coding: utf-8 -*-
import re
import os
import json
import time
import scrapy
import requests
from hashlib import md5
from urllib import parse
from ..util.utils import isLinux, filter_text
from ..items import ShopItem, SkuAttributesItem, SkuItem
from ..expands import MysqlParseSpider

website = 'jpcycles'
# 浏览器渲染解析脚本

class ParseSpider(MysqlParseSpider):
    name = website
    system = isLinux()
    # allowed_domains = ['jpcycles.com']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        if not cls.system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"

            custom_debug_settings["DOWNLOADER_MIDDLEWARES"] = {
                'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            }
            custom_debug_settings["ITEM_PIPELINES"] = {
            # 'overseaSpider.pipelines.WeshopSpiderPipeline': 300,
            }
        else:
            # 服务器配置
            custom_debug_settings["WEBSITE"] = website
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["DOWNLOADER_MIDDLEWARES"] = {
                'overseaSpider.middlewares.WeshopDownloaderMiddleware': 543,
            }
            custom_debug_settings["ITEM_PIPELINES"] = {
            'overseaSpider.pipelines.WeshopSpiderPipeline': 300,
            }
        # 更新配置
        settings.setdict(custom_debug_settings or {}, priority='spider')
        cls.settings = settings

    def __init__(self, **kwargs):
        super(ParseSpider, self).__init__(**kwargs)
        self.counts = 0
        # 记得填名字
        setattr(self, 'author', "")

    is_debug = True
    custom_debug_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 0,
        'LOG_LEVEL': 'DEBUG',
    }

    if not system:
        def start_requests(self):
            url_list = [
                "https://www.jpcycles.com/product/530-621/kuryakyn-longhorn-offset-dually-highway-pegs-with-1-1-4-magnum-quick-clamps",
                "https://www.jpcycles.com/product/5500046/j-p-cycles-rectangular-shaker-floorboards",
            ]
            for url in url_list:
                yield scrapy.Request(
                    url=url,
                )

    def parse(self, response):
        # print(response.text)
        """详情页"""
        items = ShopItem()
        site_id = response.meta.get("site_id", None)
        task_id = response.meta.get("task_id", None)
        url = response.meta.get("url", response.url)
        # ---------------------------获取商品名字, 如果name有值则证明是详情页-----------------
        name = response.xpath("//div[@class='cell small-12']/h1/text()").get()
        if not name:
            print(f"该页面不是详情页:{url}")
            items["url"] = url
        else:
        # -----------------------------------------------------------------------------
        # 注意如果某些字段获取的时候是None,请不要赋值为None赋值为''
        # eg: brand = response.xpath("").get('')
        # -----------------------------------------------------------------------------
            items["url"] = url
            items["name"] = name
            original_price = response.xpath("//div[@class='old-price']/span/text()").get()
            current_price = response.xpath("//meta[@property='og:price:amount']/@content").get()
            items["original_price"] = str(original_price) if original_price else "$" + str(current_price)
            items["current_price"] = "$" + str(current_price) if current_price else str(original_price)
            brand = re.findall('"Brand":"(.*?)"},', response.text)
            items["brand"] = brand[0] if brand else ''
            # attributes = list()
            # items["attributes"] = attributes
            # items["about"] = response.xpath("").get()
            description_list = response.xpath("//div[@id='content-description']//text()").getall()
            description = "".join(description_list)
            items["description"] = filter_text(description)
            # items["care"] = response.xpath("").get()
            # items["sales"] = response.xpath("").get()
            items["source"] = website
            images_list = response.xpath("//div[@id='main-product-image']//img/@data-zoom").getall()
            images_list = images_list[0:int(len(images_list) / 2)]
            items["images"] = images_list
            Breadcrumb_list = response.xpath("//ul[@class='breadcrumbs']/li/a//text()").getall()
            items["cat"] = Breadcrumb_list[-1]
            items["detail_cat"] = "/".join(Breadcrumb_list)
            sku_list = list()
            items["sku_list"] = sku_list

            items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
            items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            items["created"] = int(time.time())
            items["updated"] = int(time.time())
            items['is_deleted'] = 0
            items['site_id'] = site_id
            items['task_id'] = task_id


        print(items)
        yield items