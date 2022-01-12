# -*- coding: utf-8 -*-
import html
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

# !/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File   ：templatespider -> thebookstall
@IDE    ：PyCharm
@Author ：Mr. Tutou
@Date   ：2021/12/20 12:26
@Desc   ：
=================================================='''

website = 'thebookstall'


def get_sku_price(product_id, attribute_list):
    """获取sku价格"""
    url = 'https://thecrossdesign.com/remote/v1/product-attributes/{}'.format(product_id)
    data = {
        'action': 'add',
        'product_id': product_id,
        'qty[]': '1',
    }
    for attribute in attribute_list:
        data['attribute[{}]'.format(attribute[0])] = attribute[1]
    response = requests.post(url=url, data=data)
    return json.loads(response.text)['data']['price']['without_tax']['formatted']


class ThecrossdesignSpider(scrapy.Spider):
    name = website
    allowed_domains = ['thebookstall.com']
    start_urls = ['https://www.thebookstall.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 10
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(ThecrossdesignSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "秃头")

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

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ', '$', '€']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = ['https://www.thebookstall.com/book-stall-selections']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse1)
    def parse1(self, response):
        """获取全部分类"""
        category_urls = response.xpath('//div[@class="field-item even"]/p/a/@href').getall()
        for i in range(len(category_urls)):
            category_urls[i] = self.start_urls[0] + category_urls[i]
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse2)

    def parse2(self, response):
        """获取全部分类"""
        name1 = "Home/" + response.xpath('//h1[@id="page-title"]/text()').get().strip()
        category_urls = response.xpath('//div[@class="field-item even"]/p/a/@href').getall()
        for i in range(len(category_urls)):
            category_urls[i] = self.start_urls[0] + category_urls[i]
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list, meta={"cat_name": name1})

    def parse_list(self, response):
        """商品列表页"""
        cat_name_1 = response.meta.get('cat_name')
        cat_name_1 = cat_name_1 + "/" + response.xpath('//h1[@id="page-title"]/text()').get().strip()
        detail_url_list = response.xpath('//div[@class="abaproduct-image"]/a/@href').getall()
        for i in range(len(detail_url_list)):
            detail_url_list[i] = self.start_urls[0] + detail_url_list[i]
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail, meta={"cat_name": cat_name_1})
        # next_page_url = response.xpath('//li[@class="pagination-item pagination-item--next"]/a/@href').get()
        # if next_page_url:
        #     yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath('//div[@class="abaproduct-price"]/text()').get()
        if not price:
            price = response.xpath('//span[@class="uc-price"]/text()').get()
        price = self.price_fliter(price.strip())
        items["original_price"] = price.replace(',', '').strip()
        items["current_price"] = items["original_price"]

        name = response.xpath('//h1[@id="page-title"]/text()').get()
        name = name.strip()
        items["name"] = name

        items["detail_cat"] = response.meta.get('cat_name') +"/" + name
        items["cat"] = name

        # description = ''
        description = response.xpath('//div[@class="abaproduct-body"]//text()').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = 'thebookstall.com'

        # attr1_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[1]/text()').getall()
        # attr2_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[2]/text()').getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a]+":"+attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath('//div[@class="abaproduct-image"]/a/@href').getall()
        items["images"] = images_list
        items["brand"] = ''

        items["sku_list"] = []
        # opt_name = response.xpath('//div[@class="product-variants"]/div/span/text()').getall()
        # if not opt_name:
        #     items["sku_list"] = []
        #     # return
        # else:
        #     opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
        #     opt_value = []
        #     # print(opt_name)
        #     opt_length = len(opt_name)
        #     for i in range(opt_length):
        #         value_temp = response.xpath('//div[@class="product-variants"]/div[' + str(
        #             i + 1) + ']/ul/li/label/span/text()').getall()
        #         if not value_temp:
        #             value_temp = response.xpath('//div[@class="product-variants"]/div[' + str(
        #                 i + 1) + ']/select[@class="form-control form-control-select"]/option/text()').getall()
        #         if value_temp:
        #             opt_value.append(value_temp)
        #
        #     # print(opt_value)
        #     attrs_list = []
        #     for opt in itertools.product(*opt_value):
        #         temp = dict()
        #         for i in range(len(opt)):
        #             temp[opt_name[i]] = opt[i]
        #         if len(temp):
        #             attrs_list.append(temp)
        #     # print(attrs_list)
        #
        #     sku_list = list()
        #     for attrs in attrs_list:
        #         sku_info = SkuItem()
        #         sku_attr = SkuAttributesItem()
        #         other_temp = dict()
        #
        #         for attr in attrs.items():
        #             if attr[0] == 'Talla':
        #                 sku_attr["size"] = attr[1]
        #             elif attr[0] == 'Color':
        #                 sku_attr["colour"] = attr[1]
        #             else:
        #                 other_temp[attr[0]] = attr[1]
        #         if len(other_temp):
        #             sku_attr["other"] = other_temp
        #
        #         sku_info["current_price"] = items["current_price"]
        #         sku_info["original_price"] = items["original_price"]
        #         sku_info["attributes"] = sku_attr
        #         sku_list.append(sku_info)
        #     items["sku_list"] = sku_list

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
        # item_check.check_item(items)
        # detection_main(items = items,website = website,num=self.settings["CLOSESPIDER_ITEMCOUNT"],skulist=True,skulist_attributes=True)
        # print(items)
        yield items
