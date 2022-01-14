# -*- coding: utf-8 -*-
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

website = 'hamnbone'


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
    allowed_domains = ['hamnbone.com']
    start_urls = ['https://hamnbone.com/']

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
        setattr(self, 'author', "叶石")

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
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', ', ', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = ['https://hamnbone.com/dog/',
                         'https://hamnbone.com/cat/',
                         'https://hamnbone.com/other/',
                         'https://hamnbone.com/humans/',
                         'https://hamnbone.com/dog/accessories/',
                         'https://hamnbone.com/dog/food/',
                         'https://hamnbone.com/dog/toys/',
                         'https://hamnbone.com/dog/treats/',
                         'https://hamnbone.com/cat/food/',
                         'https://hamnbone.com/cat/litter/',
                         'https://hamnbone.com/cat/toys/',
                         'https://hamnbone.com/cat/treats/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//figure[@class='product-item-thumbnail']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//nav[@class='pagination button-group']/a[last()]/@href").get()
        if next_page_url and next_page_url!="":
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='product-details-column']//span[@class='price price-without-tax']/text()").get()
        if not price:
            price = response.xpath("//div[@class='product-details-column']//span[@class='price-value']/text()").get()
        price = price.replace("\n",'')
        price = price.replace(" ",'')
        price = price.replace("$",'')
        p_split = price.split("-")
        items["original_price"] = p_split[0]
        items["current_price"] = p_split[0]
        items["brand"] = ''
        name = response.xpath("//h1[@class='product-title']/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li//span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='product-description']").get()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//a[@class='product-image']/@href").getall()
        items["images"] = images_list

        opt_name_tmp = response.xpath("//div[@class='form-field-title']/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
            o=o.replace("\n",'')
            o=o.replace(" ",'')
            if o!="":
                opt_name.append(o)
        if not opt_name:
            items["sku_list"] = []
        else:
            opt_value = []
            v_dict=dict()
            n_dict=dict()
            product_id = response.xpath("//input[@name='product_id']/@value").get()
            attr_name = response.xpath("//div[@class='form-field-control']/label/input/@name").get()
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='product-options-container']/div["+str(i+1)+"]/div[@class='form-field-control']/label/span/text()").getall()
                value_value = response.xpath("//div[@class='product-options-container']/div["+str(i+1)+"]/div[@class='form-field-control']/label/input/@value").getall()
                value_attr = response.xpath("//div[@class='product-options-container']/div["+str(i+1)+"]/div[@class='form-field-control']/label/input/@name").get()
                n_dict[opt_name[i]]=value_attr
                if value_temp:
                    opt_value.append(value_temp)
                for i in range(len(value_value)):
                    v_dict[value_temp[i]]=value_value[i]
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
                data = {
                    'action': 'add',
                    'product_id': product_id,
                    'qty[]': '1'
                }
                for attr in attrs.items():
                    if attr[0] == 'Size':
                        sku_attr["size"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                    data[n_dict[attr[0]]] = v_dict[attr[1]]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                headers = {
                    'authority': 'hamnbone.com',
                    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                    'stencil-config': '{}',
                    'x-xsrf-token': '23da4333b70c55918fb9e0e24984f6f1b97b4711878a29641639c4639f441a45',
                    'sec-ch-ua-mobile': '?0',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'x-requested-with': 'stencil-utils',
                    'stencil-options': '{"render_with":"products/add-to-cart-form"}',
                    'sec-ch-ua-platform': '"Windows"',
                    'accept': '*/*',
                    'origin': 'https://hamnbone.com',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                    'cookie': 'SHOP_SESSION_TOKEN=g2a2v4gk9lafma7n696k4le6aa; fornax_anonymousId=897950d8-d550-49fa-ab53-78bff3432815; XSRF-TOKEN=23da4333b70c55918fb9e0e24984f6f1b97b4711878a29641639c4639f441a45; STORE_VISITOR=1; landing_site=https://hamnbone.com/; lastVisitedCategory=44; Shopper-Pref=107BB9D170C8A6BD2F0234E475B67A6397BB3877-1639039240094-x%7B%22cur%22%3A%22USD%22%7D',
                }



                response1 = requests.post('https://hamnbone.com/remote/v1/product-attributes/'+product_id, headers=headers,
                                         data=data)
                r_json = json.loads(response1.text)
                sku_info["current_price"] = str(r_json['data']['price']['without_tax']['value'])
                sku_info["original_price"] = str(r_json['data']['price']['without_tax']['value'])
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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
