# -*- coding: utf-8 -*-
import itertools
import math
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'filippa-k'
website_url = 'https://www.filippa-k.com'

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
    allowed_domains = ['filippa-k.com']
    start_urls = ['https://www.filippa-k.com/']

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
        super(ThecrossdesignSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "叶复")

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
        label_pattern = [r'<div class="cbb-frequently-bought-container cbb-desktop-view".*?</div>', r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
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
        category_urls = ['/en/woman', '/en/man', '/en/soft-sport']
        for category_url in category_urls:
            category_url = website_url + category_url
            yield scrapy.Request(url=category_url, callback=self.prase_cal, meta={'url':category_url})

    def prase_cal(self,response):
        URL = response.meta.get('url')
        number_str = response.xpath("//div[@class='cg ch ci']/text()").get()
        number_str = int(re.search(r'\d+',number_str).group())
        number = math.ceil(number_str/24)*24
        url = URL + '?sortBy=popularity&count=' + str(number)
        yield scrapy.Request(url=url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='bg b c d']/div/a[@class='b c bg e3 e4 e5 dg']/@href").getall()
        for detail_url in detail_url_list:
            detail_url = website_url + detail_url
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        web_str = re.search(r'CURRENT_PAGE = (.*?);',response.text).group(1)
        web_json = json.loads(web_str)
        # price = response.xpath("//div[@class='h an jm j1 j2 j3 j4 j5 jn jo j6 jp jq ab ac']/div/span/span[@class='b9 dx']/text()").get()
        # price = price.replace('$','')
        items["original_price"] = str(web_json['price']['original'])
        items["current_price"] = str(web_json['price']['current'])
        name = web_json['displayName']
        items["name"] = name
        items["brand"] = web_json['trackingProduct']['brand']
        cat_list = response.xpath("//ul[@class='bc bd be bf bg b bh bi t u bj bk bl bm']/li/a/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = str(web_json['description']['html'])
        # items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["description"] = description
        items["source"] = website

        images_list = web_json['imageUrls']
        for i in range(len(images_list)):
            images_list[i] = website_url + images_list[i]
        items["images"] = images_list
        has_size = web_json['hasSizes']
        opt_name = []
        attrs_list = []
        if has_size:
            opt_name = ['size', 'color']
            opt_value = []
            size_list = web_json['listItem']['preloaded']['items']
            value_size = []
            for size in size_list:
                value_size.append(size['displayName'])
            opt_value.append(value_size)
            value_color = []
            value_color.append(web_json['color'])
            color_dict = dict()
            tmp_dict = dict()
            tmp_dict['img_list'] = images_list
            tmp_dict['price'] = items['current_price']
            color_dict[web_json['color']] = tmp_dict
            color_list = web_json['articles']
            if len(color_list) != 0:
                for i in color_list:
                    value_color.append(i['color'])
                    tmp_dict0 = dict()
                    images_list0 = i['imageUrls']
                    for c in range(len(images_list0)):
                        images_list0[c] = website_url + images_list0[c]
                    tmp_dict0['img_list'] = images_list0
                    tmp_dict0['price'] = str(i['price']['current'])
                    color_dict[i['color']] = tmp_dict0
            opt_value.append(value_color)
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
        else:
            opt_name = ['color']
            opt_value = []
            value_color = []
            value_color.append(web_json['color'])
            color_dict = dict()
            tmp_dict = dict()
            tmp_dict['img_list'] = images_list
            tmp_dict['price'] = items['current_price']
            color_dict[web_json['color']] = tmp_dict
            color_list = web_json['articles']
            if len(color_list) != 0:
                for i in color_list:
                    value_color.append(i['color'])
                    tmp_dict0 = dict()
                    images_list0 = i['imageUrls']
                    for c in range(len(images_list0)):
                        images_list0[c] = website_url + images_list0[c]
                    tmp_dict0['img_list'] = images_list0
                    tmp_dict0['price'] = str(i['price']['current'])
                    color_dict[i['color']] = tmp_dict0
            opt_value.append(value_color)
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


            for attr in attrs.items():
                if attr[0] == 'size':
                    sku_attr["size"] = attr[1]
                elif attr[0] == 'color':
                    sku_attr["colour"] = attr[1]
                    sku_info["current_price"] = color_dict[attr[1]]['price']
                    sku_info["original_price"] = color_dict[attr[1]]['price']
                    sku_info["imgs"] = color_dict[attr[1]]['img_list']

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
        detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
