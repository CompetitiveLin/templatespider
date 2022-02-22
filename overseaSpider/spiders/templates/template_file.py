# -*- coding: utf-8 -*-
import re
import time
import json
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
import logging

from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem


logger = logging.getLogger(__name__)
website = ''

# 全流程解析脚本
class OverseaSpider(scrapy.Spider):
    name = website
    # start_urls = ['http://acnestudios.com/']


    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(OverseaSpider, self).__init__(**kwargs)
        self.counts = 0
        self.temp_version = '1.0'

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },

    }

    def start_requests(self):
        url = "https://www.hsn.com/store-directory#"
        yield scrapy.Request(
            url=url,
        )

    def parse(self, response):
        """主页"""
        url_list = response.xpath("").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            logger.debug(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("").getall()
        detail_url_list = [response.urljoin(url) for url in detail_url_list]
        for detail_url in detail_url_list:
            detail_url = response.urljoin(detail_url)
            logger.debug("详情页url:"+detail_url)
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail
            )

        next_page_url = response.xpath("").get()
        if next_page_url:
            next_page_url = response.urljoin(next_page_url)
            logger.info("下一页:"+next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        json_str = re.findall("var dataLayer = \[([\s\S]*?)\];", response.text)
        json_data = json.loads(json_str[0]) if json_str else None
        # logger.debug(json_data)
        if json_data:
            items["brand"] = json_data["product_brand"][0]
            items["name"] = json_data["product_name"][0]
            original_price = json_data["product_original_price"][0]
            current_price = json_data["product_sale_price"][0]
            items["detail_cat"] = json_data["product_primary_category_name"][0]
            items["cat"] = json_data["categories"][0][0]["Name"]
            images_list = json_data["product_image_url"]
            items["images"] = images_list

        items["url"] = response.url
        items["original_price"] = str(original_price)
        items["current_price"] = str(current_price)
        items["source"] = website
        about = response.xpath("").getall()
        items["about"] = "".join(about).strip().replace("\n", "").replace("\r", "").replace("\xa0", "")

        description = response.xpath("").getall()
        items["description"] = "".join(description).strip().replace("\n", "").replace("\r", "").replace("\xa0", "")

        sku_list = list()
        color_label_list = response.xpath("//div[@class='color-option']/label")
        logger.debug(len(color_label_list))
        if color_label_list:
            for color_label in color_label_list:
                sku_item = SkuItem()
                sku_item["original_price"] = original_price
                sku_item["current_price"] = current_price
                sku_item["url"] = response.url
                images_json = color_label.xpath("./input/@data-images").get()
                sku_item["imgs"] = json.loads(images_json)["detail"]

                attributes = SkuAttributesItem()
                colours = color_label.xpath("./span/text()").getall()
                attributes["colour"] = "".join(colours).strip()
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)

        else:
            sku_item = SkuItem()
            sku_item["original_price"] = original_price
            sku_item["current_price"] = current_price
            sku_item["url"] = response.url
            sku_item["imgs"] = items["images"]
            attributes = SkuAttributesItem()
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
        # logger.debug(items)
        yield items


