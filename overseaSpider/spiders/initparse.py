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

website = 'initparse'
# 浏览器渲染解析脚本

class ParseSpider(MysqlParseSpider):
    name = website
    system = isLinux()
    # allowed_domains = ['initparse.com']

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
            # 填入该网站5个不同类型的详情页url
            url_list = [

            ]
            for url in url_list:
                yield scrapy.Request(
                    url=url,
                )

    def parse_detail(self, response):
        # print(response.text)
        """详情页"""
        items = ShopItem()
        site_id = response.meta.get("site_id", None)
        task_id = response.meta.get("task_id", None)
        url = response.meta.get("url", response.url)
        # ---------------------------获取商品名字, 如果name有值则证明是详情页-----------------
        name = response.xpath("").get()
        if not name:
            print(f"该页面不是详情页:{url}")
            items["url"] = url
        else:
        # -----------------------------------------------------------------------------
        # 注意如果某些字段获取的时候是None,请不要赋值为None, 赋值为''
        # eg: brand = response.xpath("").get('')
        # -----------------------------------------------------------------------------
            items["url"] = url
            items["name"] = name
            # price = re.findall("", response.text)[0]
            original_price = response.xpath("").get()
            current_price = response.xpath("").get()
            items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
            items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
            items["brand"] = response.xpath("").get()
            items["name"] = response.xpath("").get()
            attributes = list()
            items["attributes"] = attributes
            items["about"] = response.xpath("").get()
            items["description"] = response.xpath("").get()
            items["care"] = response.xpath("").get()
            items["sales"] = response.xpath("").get()
            items["source"] = website
            images_list = response.xpath("").getall()
            items["images"] = images_list

            Breadcrumb_list = response.xpath("").getall()
            items["cat"] = Breadcrumb_list[1]
            items["detail_cat"] = Breadcrumb_list[-1]

            sku_list = list()
            # sku实例字段, 如果有sku信息,价格字段必须要有
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
            items['site_id'] = site_id
            items['task_id'] = task_id

        print(items)
        yield items