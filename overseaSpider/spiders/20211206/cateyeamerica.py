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

website = 'cateyeamerica'


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
    allowed_domains = ['cateyeamerica.com']
    start_urls = ['https://www.cateyeamerica.com/']

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

    def filter_html_label(self, text):
        text = str(text)
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
        text = html.unescape(text)
        text = re.sub(' +', ' ', text).strip()
        return text

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//a[@class='navPage-subMenu-action navPages-action']/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='product']//figure/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='productView-product']//span[@data-product-price-without-tax]/text()").get()
        price = self.filter_text(price)
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li//span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='cus_shortdesc']").getall()

        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        if items["description"] == "":
            description = response.xpath("//div[@itemprop='description']").getall()
            items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//li[@class='productView-thumbnail']/a/@href").getall()
        items["images"] = images_list
        items["brand"] = ''

        opt_name_tmp = response.xpath("//div[@class='productView-options-inner']/div/label/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
            if o.find(":")!=-1:
                opt_name.append(o)
        if not opt_name:
            items["sku_list"] = []
        else:
            for o in range(len(opt_name)):
                opt_name[o] = opt_name[o].replace("\n","")
                opt_name[o] = opt_name[o].replace(":","")
                opt_name[o] = opt_name[o].strip()
            product_id = response.xpath("//input[@name='product_id']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='productView-options-inner']/div["+str(i+1)+"]/select/option[@data-product-attribute-value]/text()").getall()
                value_value = response.xpath("//div[@class='productView-options-inner']/div["+str(i+1)+"]/select/option[@data-product-attribute-value]/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]]=value_value[v]
                attr_name = response.xpath("//div[@class='productView-options-inner']/div["+str(i+1)+"]/select/@name").get()
                attr_dict[opt_name[i]]=attr_name
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
            headers = {
                'authority': 'www.cateyeamerica.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'stencil-config': '{}',
                'x-xsrf-token': 'b209b6f28ebcb4452c6ec8c746abbd940bf5f9577069bca41a281de94ac47f18, b209b6f28ebcb4452c6ec8c746abbd940bf5f9577069bca41a281de94ac47f18',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'stencil-options': '{"render_with":"products/bulk-discount-rates"}',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://www.cateyeamerica.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'SHOP_SESSION_TOKEN=e44454oo2o7i0cskp6f2n3metp; fornax_anonymousId=258fe811-fc55-4005-88ad-4f485b5132f5; _gcl_au=1.1.30781741.1638841610; rsci_vid=893d9f06-002c-c8f1-f4b0-c22359fa4229; tracking-preferences={%22version%22:1%2C%22destinations%22:{}%2C%22custom%22:{%22marketingAndAnalytics%22:true%2C%22advertising%22:true%2C%22functional%22:true}}; bc_consent=%7B%22allow%22%3A%5B3%2C4%2C2%5D%2C%22deny%22%3A%5B%5D%7D; STORE_VISITOR=1; XSRF-TOKEN=b209b6f28ebcb4452c6ec8c746abbd940bf5f9577069bca41a281de94ac47f18; ajs_group_id=null; ajs_user_id=null; ajs_anonymous_id=%229c0dc387-bae3-43f9-b219-7a8095017f9e%22; _ga=GA1.2.1258495404.1638927909; _gid=GA1.2.1830002483.1638927909; displayedPopupNewsletter=yes; lastVisitedCategory=38; Shopper-Pref=56C97A49EDDB2C325143E816491E5604ADD97F50-1639534480485-x%7B%22cur%22%3A%22USD%22%7D; _gali=attribute_select_135',
            }
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
                    data[attr_dict[attr[0]]]=value_dict[attr[1]]
                    if attr[0].find("Size")!=-1:
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://www.cateyeamerica.com/remote/v1/product-attributes/'+product_id,
                                         headers=headers, data=data)
                sku_json = json.loads(response.text)
                data_json = sku_json["data"]
                sku_info["current_price"] = str(data_json["price"]["without_tax"]["value"])
                sku_info["original_price"] = str(data_json["price"]["without_tax"]["value"])
                sku_info["attributes"] = sku_attr
                if "image" in data_json:
                    if data_json["image"] is not None:
                        img = data_json["image"]["data"]
                        img = img.replace("{:size}","1280x1280")
                        img_list = [img]
                        sku_info["imgs"] = img_list

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
