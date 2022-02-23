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
from copy import deepcopy
from lxml import etree

website = 'massaboutique'
scheme = 'https://www.massaboutique.eu/'


class EkobiecaSpider(scrapy.Spider):
    name = website
    allowed_domains = ['massaboutique.eu/']
    start_urls = ['https://www.massaboutique.eu/']

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
        super(EkobiecaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "哲夫")

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT': 10,
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

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//ul[@class='noborder ']//a/@href").getall()
        for category_url in category_urls:
            if not category_url.startswith('http'):
                category_url = scheme + category_url
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='item_list']/div/div/a/@href").getall()
        for detail_url in detail_url_list:
            if not detail_url.startswith('http'):
                detail_url = scheme + detail_url
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail,
                dont_filter=True,
            )

    def parse_detail(self, response):
        item = ShopItem()
        item["source"] = website  # 来自哪个网站
        item["name"] = response.xpath("//h1[@id='brand']//span/text()").get().replace("\n", "")
        item["brand"] = deepcopy(item["name"])
        category_list = response.xpath("//div[@class='barra_navigator']//span/a/span/text()").getall()
        item["cat"] = category_list[-1]
        detail_cate = category_list[0]
        for i in range(1, len(category_list), 1):
            detail_cate += '/' + category_list[i]
        item["detail_cat"] = deepcopy(detail_cate)
        item["measurements"] = ['Height: None', 'Length: None', 'Depth: None', 'Weight: None']
        item["description"] = response.xpath("//h1[@id='brand']/span[@id='nome_prodotto']/text()").get().replace("\t",
                                                                                                           "")  # 介绍文案
        item["description"] = item["description"].replace("\r\n", "")
        # item["description"] = response.xpath("//div[@class='whyWeLoveIt-message']/p/text()").get().replace("\n", "")
        item["url"] = response.url
        price = response.xpath('//span[@class="prezzopieno"]/text()').get()
        item["original_price"] = self.price_fliter(price)  # 原价
        item["current_price"] = self.price_fliter(price)

        images_list = response.xpath('//div[@id="gallery_01"]/a/@data-image').getall()
        item["images"] = images_list

        status_list = list()
        status_list.append(item["url"])
        status_list.append(item["original_price"])
        status_list.append(item["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        item["id"] = md5(status.encode("utf8")).hexdigest()

        item["sku_list"] = list()
        sku_list = response.xpath("//div[@class='taglie']/ul/li/a/@href").getall()
        sku_list = [response.urljoin(one_sku) for one_sku in sku_list]

        sku_item = SkuItem()
        item_arr = SkuAttributesItem()
        images = response.xpath("//div[@class='foto_grande ']/div/img/@src").getall()  # 商品图片
        sku_item["imgs"] = deepcopy(images)
        sku_item["url"] = response.url
        # price = response.xpath("//div[@class='prezzo']/div/span/text()").getall()
        # price = [i.replace("\n", "") for i in price]
        # price = ''.join(price)
        sku_item["original_price"] = self.price_fliter(price)  # 原价
        sku_item["current_price"] = self.price_fliter(price)
        item_arr['colour'] = response.xpath("//div[@class='taglie']/ul/li/span/text()").get()
        sku_item["attributes"] = item_arr
        item["sku_list"].append(sku_item)

        if sku_list:
            for key in sku_list:
                res = requests.get(url=key)
                sth = etree.HTML(res.text)

                sku_item = SkuItem()
                item_arr = SkuAttributesItem()
                images = sth.xpath("//div[@class='foto_grande ']/div//img/@src")  # 商品图片
                sku_item["imgs"] = deepcopy(images)
                sku_item["url"] = key
                sku_item["original_price"] = self.price_fliter(price)  # 原价
                sku_item["current_price"] = self.price_fliter(price)

                item_arr['colour'] = sth.xpath("//div[@class='taglie']/ul/li/span/text()")[0]
                sku_item["attributes"] = item_arr

                item["sku_list"].append(sku_item)

        item["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        item["created"] = int(time.time())
        item["updated"] = int(time.time())
        item['is_deleted'] = 0

        # detection_main(items=item,
        #                website=website,
        #                num=self.settings["CLOSESPIDER_ITEMCOUNT"],
        #                skulist=True,
        #                skulist_attributes=True)
        # print(item)
        yield item
