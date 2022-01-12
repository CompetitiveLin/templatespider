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
@Project -> File   ：templatespider -> ecocandleco
@IDE    ：PyCharm
@Author ：Mr. Tutou
@Date   ：2021/12/20 15:55
@Desc   ：
=================================================='''

website = 'ecocandleco'


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
    allowed_domains = ['ecocandleco.com']
    start_urls = ['https://ecocandleco.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 3
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
        category_urls = ['https://ecocandleco.com/candles/','https://ecocandleco.com/home-fragrance/','https://ecocandleco.com/bath-body/','https://ecocandleco.com/new-seasonal/','https://ecocandleco.com/home-goods/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath('//h4[@class="card-title"]/a/@href').getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath('//li[@class="pagination-item pagination-item--next"]//@href').get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath('//div[@itemprop="offers"]/span[@class="price price--withoutTax"]//text()').get()
        price = price if '-' not in price else price.split('-')[0]
        items["current_price"] = self.price_fliter(price)
        original_price = response.xpath('//div[@class="productView-price"]//span[@class="price price--non-sale"]/text()').get().strip()
        if original_price:
            items["original_price"] = self.price_fliter(original_price)
        else:
            items["original_price"] = items["current_price"]

        name = response.xpath('//h1[@itemprop="name"]/text()').get()

        items["name"] = name

        cat_list = response.xpath('//ul[@class="breadcrumbs"]//span/text()').getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath('//div[@id="tab-description"]//span/text()').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = 'ecocandleco.com'

        # attr1_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[1]/text()').getall()
        # attr2_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[2]/text()').getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a]+":"+attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath('//li[@class="productView-thumbnail"]/a/@href').getall()
        items["images"] = images_list
        items["brand"] = ''


        opt_name = response.xpath('//label[@class="form-label form-label--alternate form-label--inlineSmall"]/text()').getall()
        opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
        if not opt_name:
            items["sku_list"] = []
            # return
        else:
            opt_value = []
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = ""
                if opt_name[i].lower() == "choose your fragrance":
                    value_temp = response.xpath('//select[@class="form-select form-select--small"]/option/text()').getall()[1:]
                elif opt_name[i] == "Choose your color":
                    value_temp = response.xpath('//span[@class="form-option-variant"]/text()').getall()
                elif opt_name[i] == "Box or no box?":
                    value_temp = response.xpath('//label[@class="form-label"]/text()').getall()
                if value_temp:
                    opt_value.append(value_temp)

            # print(opt_value)
            attrs_list = []
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
            # print(attrs_list)

            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'Talla':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Choose your color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["url"] = response.url
                sku_info["attributes"] = sku_attr
                sku_list.append(sku_info)
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
        # item_check.check_item(items)
        # detection_main(items = items,website = website,num=self.settings["CLOSESPIDER_ITEMCOUNT"],skulist=True,skulist_attributes=True)
        # print(items)
        yield items
