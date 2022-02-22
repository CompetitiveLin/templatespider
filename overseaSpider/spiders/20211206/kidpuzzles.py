# -*- coding: utf-8 -*-
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'kidpuzzles'


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
    allowed_domains = ['kidpuzzles.com']
    start_urls = ['https://www.kidpuzzles.com/']

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
        category_urls = ['https://www.kidpuzzles.com/wooden-puzzles/',
                         'https://www.kidpuzzles.com/personalized-name-puzzles/',
                         'https://www.kidpuzzles.com/3d-puzzles/',
                         'https://www.kidpuzzles.com/name-puzzle-stools/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//h4[@class='listItem-title']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-item pagination-item--next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//meta[@itemprop='price']/@content").get()
        if price_new==0:
            return
        price_new = str(price_new)
        price_old = response.xpath("//div[@class='productView']//span[@class='price price--rrp']/text()").get()
        if price_old:
            price_old=price_old.replace("$",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li/a/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@id='tab-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//li[@class='productView-thumbnail']/a/@href").getall()
        if not images_list:
            images_list=response.xpath("//img[@class='productView-image--default']/@src").getall()
        items["images"] = images_list
        items["brand"] = 'KidPuzzles'

        opt_name1 = response.xpath("//div[@class='productView-options']/form[1]//label[@class='form-label form-label--alternate form-label--inlineSmall']/text()").get()
        opt_name = []
        opt_name.append(opt_name1)
        # print(opt_name)
        if not opt_name1:
            items["sku_list"] = []
        else:
            for o in range(len(opt_name)):
                opt_name[o]=opt_name[o].replace("\n",'')
                opt_name[o]=opt_name[o].strip()
                opt_name[o]=opt_name[o].replace(":",'')
            opt_value = []
            value_name = response.xpath("//div[@class='productView-options']/form[1]//input[@type='radio']/@name").get()
            product_id = response.xpath("//div[@class='productView-options']/form[1]//input[@name='product_id']/@value").get()
            value_dict = dict()
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='productView-options']/form[1]//label[@data-product-attribute-value]/text()").getall()
                # print(value_temp)
                if value_temp:
                    opt_value.append(value_temp)
                value_value = response.xpath("//div[@class='productView-options']/form[1]//input[@type='radio']/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]]=value_value[v]
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
                    other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                headers = {
                    'authority': 'www.kidpuzzles.com',
                    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                    'stencil-config': '{}',
                    'x-xsrf-token': '4795411547970346487e6c82e567b47c7b86177bcad6e3f8ad922871d5aa4f90, 4795411547970346487e6c82e567b47c7b86177bcad6e3f8ad922871d5aa4f90',
                    'sec-ch-ua-mobile': '?0',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'accept': '*/*',
                    'x-requested-with': 'XMLHttpRequest',
                    'stencil-options': '{}',
                    'sec-ch-ua-platform': '"Windows"',
                    'origin': 'https://www.kidpuzzles.com',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                    'cookie': 'SHOP_SESSION_TOKEN=sg20epieq8s4sis1t7n95unsqh; fornax_anonymousId=baf31ad5-c5fe-4100-b926-17a2af2b3674; _ga=GA1.2.1533766256.1637918483; SHOP_SESSION_ROTATION_TOKEN=ae633530cd4cee87fc99887557cdab6ed1bd1dd1876f1e995c3a6d8890157a40; _gid=GA1.2.1415625892.1638177510; STORE_VISITOR=1; XSRF-TOKEN=4795411547970346487e6c82e567b47c7b86177bcad6e3f8ad922871d5aa4f90; _gat=1; lastVisitedCategory=22; Shopper-Pref=B3126B753367CEA642ED8E511AAF8C90AD19F3C4-1638857290346-x%7B%22cur%22%3A%22USD%22%7D; __atuvc=2%7C47%2C18%7C48; __atuvs=61a5bf2845259aef007; _uetsid=51cdd2e050f511ec96f509699a8d4feb; _uetvid=39450e604e9a11ec8695354c4e0a8b51',
                }
                data = {}
                for attr in attrs.items():
                    data = {
                        'action': 'add',
                        value_name: value_dict[attr[1]],
                        'product_id': str(product_id),
                        'qty[]': '1'
                    }
                url = 'https://www.kidpuzzles.com/remote/v1/product-attributes/'+str(product_id)
                response = requests.post(url=url, headers=headers,
                                             data=data)
                v_json = json.loads(response.text)
                price_new1 = v_json['data']['price']["sale_price_without_tax"]['value']
                price_old1 = ''
                if "rrp_without_tax" in v_json['data']['price']:
                    price_old1=v_json['data']['price']["rrp_without_tax"]['value']
                if price_old1!="":
                    sku_info["original_price"] = str(price_old1)
                else:
                    sku_info["original_price"] = str(price_new1)
                sku_info["current_price"] = str(price_new1)
                img_list = []
                img = v_json['data']['image']['data']
                img = img.replace("{:size}","500x659")
                img_list.append(img)
                sku_info["imgs"] = img_list
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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
