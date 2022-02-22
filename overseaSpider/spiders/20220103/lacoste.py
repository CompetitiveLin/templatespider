# -*- coding: utf-8 -*-
import html
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from lxml import etree

from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'lacoste'


class LacosteSpider(scrapy.Spider):
    name = website

    # allowed_domains = ['lacoste.com']
    # start_urls = ['http://lacoste.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(LacosteSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "云棉")

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT': 10,
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
        # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        url_list = [
            'https://www.lacoste.com/us/lacoste/men/clothing/',
            'https://www.lacoste.com/us/lacoste/men/shoes/',
            'https://www.lacoste.com/us/lacoste/men/accessories/',
            'https://www.lacoste.com/us/lacoste/men/leather-goods/',
            'https://www.lacoste.com/us/lacoste/women/clothing/',
            'https://www.lacoste.com/us/lacoste/women/shoes/',
            'https://www.lacoste.com/us/lacoste/women/accessories/',
            'https://www.lacoste.com/us/lacoste/women/leather-goods/',
            'https://www.lacoste.com/us/lacoste/kids/boys/',
            'https://www.lacoste.com/us/lacoste/kids/girls/',
            'https://www.lacoste.com/us/lacoste/kids/shoes/',
            'https://www.lacoste.com/us/lacoste/kids/accessories/',
            'https://www.lacoste.com/us/lacoste/sale/kids--sale-2/',
            'https://www.lacoste.com/us/lacoste/sale/women-s-sale-2/',
            'https://www.lacoste.com/us/lacoste/sale/men-s-sale-2/',
            'https://www.lacoste.com/us/lacoste/men/accessories/',
            'https://www.lacoste.com/us/lacoste/women/accessories/',
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
            )

    def parse(self, response):
        url_list = response.xpath('//div[@class="l-relative l-overflow-hidden l-vmargin--small"]/a/@href').getall()
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_page_url = response.xpath('//a[@class="pagination-item-nude"]/@href').get()
        if next_page_url:
            next_page_url = 'https://www.lacoste.com' + next_page_url
            # print("下一页:"+next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
            )
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

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        # # price = re.findall("", response.text)[0]
        original_price = response.xpath(
            '//p[@class="nowrap fs--small text-grey-light strikethrough"]/text()').get()
        current_price = response.xpath('//p[@class="nowrap fs--medium ff-semibold l-hmargin--small"]/text()').get()
        if original_price:
            original_price = self.price_fliter(original_price)
            current_price = self.price_fliter(current_price)
        else:
            current_price = self.price_fliter(current_price)
            original_price = current_price
        items["original_price"] = original_price
        items["current_price"] = current_price
        name_info = response.xpath('//h1[@class="title--medium l-vmargin--medium padding-m-1"]/text()').get()
        name = self.filter_html_label(name_info)
        items["name"] = name
        items["brand"] = 'lacoste'
        attr = response.xpath(
            '//ul[@class="dashed-list fs--medium text-grey l-vmargin-row-1 l-vmargin-row-m-3"]//li').getall()
        attributes = list()
        for att in attr:
            att = self.filter_html_label(att)
            if att != '':
                attributes.append(att)
        items["attributes"] = attributes
        items["source"] = website
        items["description"] = ''
        images_info = response.xpath('//div[@class="slide"]//img/@data-src').getall()
        i1 = response.xpath('//img[@class="js-zoomable-img l-relative l-fill-width cursor-zoom-in"]/@src').get()
        images_info.append(i1)
        images_list = list()
        for image in images_info:
            image = 'https:' + image
            images_list.append(image)
        items["images"] = images_list
        cat_info = response.xpath('//a[@class="breadcrumb-item js-track"]/text()').getall()
        cat_list = list()
        for cat in cat_info:
            cat = self.filter_html_label(cat)
            cat_list.append(cat)
        items["cat"] = name
        items["detail_cat"] = ''.join(i + '/' for i in cat_list)[:-1] + '/' +name

        sku_list = list()
        size_info = response.xpath('//li[@class="l-vmargin--xxlarge l-hmargin--small"]/button/text()').getall()
        size_list = list()
        for size in size_info:
            size = self.filter_html_label(size)
            size_list.append(size)
        color_url = response.xpath('//li[@class="l-inline-block l-vmargin--xsmall l-hmargin--small"]/a/@href').getall()
        if color_url:
            for url in color_url:
                res = requests.get(url)
                html = etree.HTML(res.text, parser=etree.HTMLParser(encoding='utf-8'))
                sku_ori_price = html.xpath(
                    '//p[@class="nowrap fs--xsmall text-grey-light strikethrough l-vmargin--small"]/text()')
                sku_cur_price = html.xpath('//p[@class="nowrap fs--medium ff-semibold"]/text()')
                if sku_ori_price:
                    sku_ori_price = self.price_fliter(sku_ori_price[0])
                    sku_cur_price = self.price_fliter(sku_cur_price[0])
                else:
                    sku_cur_price = self.price_fliter(sku_cur_price[0])
                    sku_ori_price = sku_cur_price
                sku_image_info = html.xpath('//div[@class="slide"]//img/@data-src')
                sku_image_list = list()
                for image in sku_image_info:
                    image = 'https:' + image
                    sku_image_list.append(image)
                for size in size_list:
                    itemsb = SkuAttributesItem()
                    itemsa = SkuItem()
                    itemsa["original_price"] = sku_ori_price
                    itemsa["current_price"] = sku_cur_price
                    itemsa['imgs'] = sku_image_list
                    itemsb['size'] = size
                    itemsa['attributes'] = itemsb
                    sku_list.append(itemsa)
                if sku_list != None:
                    items['sku_list'] = sku_list
        else:
            for size in size_list:
                itemsb = SkuAttributesItem()
                itemsa = SkuItem()
                itemsa["original_price"] = original_price
                itemsa["current_price"] = current_price
                itemsa['imgs'] = []
                itemsb['size'] = size
                itemsa['attributes'] = itemsb
                sku_list.append(itemsa)
            if sku_list != None:
                items['sku_list'] = sku_list

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

        # print(items)
        # item_check.check_item(items)
        # detection_main(
        #     items=items,
        #     website=website,
        #     num=self.settings["CLOSESPIDER_ITEMCOUNT"],
        #     skulist=True,
        #     skulist_attributes=True
        # )
        yield items
