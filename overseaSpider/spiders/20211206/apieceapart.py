# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'apieceapart'

class ApieceapartSpider(scrapy.Spider):
    name = website
    allowed_domains = ['apieceapart.com']
    start_urls = ['https://www.apieceapart.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(ApieceapartSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "方尘")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': True,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
    }

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
        for pattern in label_pattern:
            labels = re.findall(pattern, text, re.S)
            for label in labels:
                text = text.replace(label, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

    def filter_text(self, input_text):
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//ul[@class='menu menu-level-2']/li/a/@href").getall()
        for category_url in category_urls:
            if category_url.startswith('/shop/'):
                yield scrapy.Request(
                    url='https://www.apieceapart.com' + category_url,
                    callback=self.parse_list,
                    meta={'detail_cat': category_url[1:]}
                )

    def parse_list(self, response):
        """商品列表页"""
        detail_cat = response.meta.get('detail_cat')
        detail_url_list = response.xpath("//div[@class='view-content']//a[@class='product-link-wrapper']/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(
                url='https://www.apieceapart.com' + detail_url,
                callback=self.parse_detail,
                meta={'detail_cat': detail_cat}
            )
        next_page_url = response.xpath('//li[@class="pager__item pager__item--next"]/a/@href').get()
        if next_page_url:
            yield scrapy.Request(
                url='https://www.apieceapart.com' + next_page_url,
                callback=self.parse_list,
                meta={'detail_cat': detail_cat}
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        json_text = re.search(r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>', response.text).group(1)
        json_data = json.loads(json_text)['storefront']

        items["current_price"] = '$' + json_data['currentVariant']['price']
        items["original_price"] = items["current_price"]

        items["name"] = json_data['product']['title']

        items["detail_cat"] = response.meta.get('detail_cat')
        items["cat"] = items["detail_cat"].split('/')[-1]

        items["description"] = json_data['product']['description']
        items["source"] = website

        brand = re.search(r'"@type": "Brand",\s+"name": "(.*?)"\s+},', response.text, re.M)
        if brand:
            items["brand"] = brand.group(1)

        items["sku_list"] = self.parse_sku(json_data)

        items["images"] = response.xpath('//ul[@class="slides"]/li/@data-thumb').getall()

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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        print(items)
        yield items

    def parse_sku(self, json_data):
        """获取sku信息"""
        images = json_data['product']['images']
        variants = json_data['product']['variants']
        sku_list = list()
        for variant in variants:
            sku_info = SkuItem()
            sku_attr = SkuAttributesItem()
            for option in variant['selectedOptions']:
                label = option['name']
                label_value = option['value']
                if label.lower() == 'color' and label_value:
                    sku_attr["colour"] = label_value
                elif label.lower() == 'size' and label_value:
                    sku_attr["size"] = label_value
                elif label_value:
                    sku_attr["other"] = {'other': label_value}
            sku_info["current_price"] = '$' + variant['price']
            sku_info["original_price"] = sku_info["current_price"]
            sku_info["imgs"] = [img['src'] for img in images if (img['altText'] or '').lower() == sku_attr.get('colour', '').lower()]
            sku_info["attributes"] = sku_attr
            sku_list.append(sku_info)
        return sku_list
