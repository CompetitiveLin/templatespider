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

website = 'schnees'


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
    allowed_domains = ['schnees.com']
    start_urls = ['https://schnees.com/']

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
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', ', ', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = ['https://schnees.com/elk-patch-trucker/',
                         'https://schnees.com/schnees-boots/logo-apparel/',
                         'https://schnees.com/hunt/',
                         'https://schnees.com/mens/',
                         'https://schnees.com/optics/',
                         'https://schnees.com/womens/',
                         'https://schnees.com/outdoors/',
                         'https://schnees.com/collections/',
                         'https://schnees.com/sale/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='product']/article/figure/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-item pagination-item--next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//section[@class='productView-details']//div[@class='price-section price-section--withoutTax']/span[@class='price price--withoutTax']/text()").get()
        price_new = self.filter_text(price_new)
        price_new = price_new.replace("\n", '')
        price_old = response.xpath("//section[@class='productView-details']//div[@class='price-section price-section--withoutTax non-sale-price--withoutTax' and not(@style)]/span[@class='price price--non-sale']/text()").get()
        if price_old:
            price_old = self.filter_text(price_old)
            price_old = price_old.replace("\n",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li//span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//article[@class='productView-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//li[@class='productView-thumbnail']/a/@href").getall()
        items["images"] = images_list
        items["brand"] = response.xpath("//h2//span[@itemprop='name']/text()").get()

        opt_name_tmp = response.xpath("//div[@data-product-option-change]/div/label[@class='form-label form-label--alternate form-label--inlineSmall']/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
           if o.find(":")!=-1:
               o = o.replace("\n",'')
               opt_name.append(o)

        if not opt_name:
            items["sku_list"] = []
        else:
            opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            attr_dict = dict()
            value_dict = dict()
            product_id = response.xpath("//input[@name='product_id']/@value").get()
            for i in range(opt_length):
                value_temp = response.xpath("//div[@data-product-option-change]/div["+str(i+1)+"]/label[@class='form-option']/span/text()").getall()
                value_value = response.xpath("//div[@data-product-option-change]/div["+str(i+1)+"]/label[@class='form-option']/@data-product-attribute-value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]]=value_value[v]
                attr_name = response.xpath("//div[@data-product-option-change]/div["+str(i+1)+"]/input/@name").get()
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
                'authority': 'schnees.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'x-xsrf-token': 'dca05d0e50b0c26e809a9e689f3d99e26fae738fff24844acedcf53bee0ad9c0, 68a029b67e56429aa4940432015a28880834307f40d49f6e19279e12a067b870',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'x-requested-with': 'XMLHttpRequest',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://schnees.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'SHOP_SESSION_TOKEN=vahos4jk1bt4t1ctm6ds2sb8im; fornax_anonymousId=7f1ef432-f3d2-406a-8dd8-b33e67e3e60e; ajs_user_id=null; ajs_group_id=null; ajs_anonymous_id=%228a378d1c-b5d9-470a-9402-22c8b3914981%22; _ga=GA1.2.1240278777.1637915328; STORE_VISITOR=1; _sp_ses.2a94=*; _gid=GA1.2.2059596264.1638762106; _clck=mpphun|1|ex1|0; tp_id=b817b56e-d26a-45d4-b636-222c8b399713; lastVisitedCategory=252; __atuvc=8%7C47%2C2%7C48%2C11%7C49; __atuvs=61ad869aed78617400a; _uetsid=6f254730564611ecba1b3320a9f2d7c5; _uetvid=df6c2d404e9211ec8c1fa91190f12bdd; __kla_id=eyIkcmVmZXJyZXIiOnsidHMiOjE2Mzc5MTUzMjgsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly9zY2huZWVzLmNvbS8ifSwiJGxhc3RfcmVmZXJyZXIiOnsidHMiOjE2Mzg3NjI2MTIsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly9zY2huZWVzLmNvbS8ifX0=; tp_referrer=5776765; _clsk=2e1rvh|1638762614445|22|1|b.clarity.ms/collect; XSRF-TOKEN=68a029b67e56429aa4940432015a28880834307f40d49f6e19279e12a067b870; _sp_id.2a94=e2bf61c6c2085fd6.1637915328.4.1638762732.1638263218; Shopper-Pref=3CC079758FE2DA2EB916E4E3303B582C53ABC6ED-1639367541850-x%7B%22cur%22%3A%22USD%22%7D; _gali=attribute_rectangle__21607_71603',
            }
            data = {
                'action': 'add',
                'product_id': product_id,
                'qty[]': '1'
            }
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    data[attr_dict[attr[0]]] = value_dict[attr[1]]
                    if attr[0] == 'Size':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://schnees.com/remote/v1/product-attributes/'+product_id, headers=headers,
                                         data=data)
                v_json = json.loads(response.text)
                sku_info["current_price"] = str(v_json["data"]["price"]["without_tax"]["value"])
                if price_old:
                    sku_info["original_price"] = str(v_json["data"]["price"]["non_sale_price_without_tax"]["value"])
                else:
                    sku_info["original_price"] = sku_info["current_price"]
                sku_info["attributes"] = sku_attr
                img_json = v_json["data"]["image"]
                img_list = []
                if img_json!=None:
                    img = img_json['data']
                    img = img.replace("{:size}",'1280x1280')
                    img_list.append(img)
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
