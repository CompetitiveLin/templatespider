# -*- coding: utf-8 -*-
import html
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from scrapy.selector import Selector
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

# !/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File   ：templatespider -> summitbrands
@IDE    ：PyCharm
@Author ：Mr. Tutou
@Date   ：2021/12/28 14:53
@Desc   ：
=================================================='''

website = 'summitbrands'


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


def convert(price):
    return '{:.2f}'.format(price)


class ThecrossdesignSpider(scrapy.Spider):
    name = website
    allowed_domains = ['summitbrands.com']
    start_urls = ['https://www.summitbrands.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 5
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
        category_urls = ['https://summitbrands.com/glisten/dishwasher-cleaner-disinfectant/',
                         'https://summitbrands.com/product/glisten-dishwasher-cleaner-freshener/',
                         'https://summitbrands.com/glisten/dishwasher-detergent-booster-freshener/',
                         'https://summitbrands.com/glisten/garbage-disposal-cleaner/',
                         'https://summitbrands.com/glisten/garbage-disposal-freshener/',
                         'https://summitbrands.com/product/glisten-cooktop-kitchen-cleaning-pads/',
                         'https://summitbrands.com/glisten/washing-machine-cleaner-deodorizer/',
                         'https://summitbrands.com/glisten/washing-machine-cleaner-freshener/',
                         'https://summitbrands.com/glisten/whirlout-jetted-bath-cleaner/',
                         'https://summitbrands.com/plink/garbage-disposal-freshener-cleaner-lemon/',
                         'https://summitbrands.com/plink/garbage-disposal-freshener-cleaner-assorted/',
                         'https://summitbrands.com/plink/garbage-disposal-freshener-cleaner-orange/',
                         'https://summitbrands.com/plink/garbage-disposal-freshener-cleaner-simply-fresh/',
                         'https://summitbrands.com/plink/fizzy-drain-freshener-cleaner-lemon/',
                         'https://summitbrands.com/plink/washer-dishwasher-freshener-cleaner/',
                         'https://summitbrands.com/product/plink-drinkware-descaler-cleaner/',
                         'https://summitbrands.com/product/plink-dishwasher-freshener-rinse-aid/',
                         'https://summitbrands.com/product/plink-bin-fresh-odor-eliminator/',
                         'https://summitbrands.com/woolite/at-home-dry-cleaner-fresh-scent/',
                         'https://summitbrands.com/woolite/at-home-dry-cleaner-fragrance-free/',
                         'https://summitbrands.com/woolite/wrinkle-static-remover-spray/',
                         'https://summitbrands.com/out-laundry/pro-wash-odor-eliminator-detergent/',
                         'https://summitbrands.com/out-laundry/white-brite-laundry-whitener/',
                         'https://summitbrands.com/iron-out-rust-stain-removers/powder/',
                         'https://summitbrands.com/iron-out-rust-stain-removers/spray/',
                         'https://summitbrands.com/iron-out-rust-stain-removers/automatic-toilet-bowl-cleaner/',
                         'https://summitbrands.com/iron-out-rust-stain-removers/outdoor/',
                         'https://summitbrands.com/iron-out-rust-stain-removers/lime-out-rust-lime-calcium-stain-remover/',
                         'https://summitbrands.com/drain-out/bathroom-drain-opener-cleaner/',
                         'https://summitbrands.com/drain-out/enzyme-drain-freshener/',
                         'https://summitbrands.com/drain-out/kitchen-drain-clog-remover-opener/',
                         'https://summitbrands.com/drain-out/septic-tank-system-treatment/',
                         'https://summitbrands.com/out-filter-mate/water-softener-cleaner-salt-booster/',
                         'https://summitbrands.com/out-filter-mate/heavy-duty-water-softener-cleaner-system-kit/',
                         'https://summitbrands.com/out-filter-mate/heavy-duty-water-softener-cleaner/',
                         'https://summitbrands.com/out-filter-mate/whole-house-scale-corrosion-system/',
                         'https://summitbrands.com/out-filter-mate/whole-house-scale-corrosion-system-cartridge/',
                         'https://summitbrands.com/out-filter-mate/sulfur-odor-neutralizer/',
                         'https://summitbrands.com/out-filter-mate/potassium-permanganate-water-treatment/',
                         'https://summitbrands.com/out-filter-mate/water-test-kit/',
                         'https://summitbrands.com/product/earthstone-multi-purpose-scouring-block/',
                         'https://summitbrands.com/product/kitchenstone-cleaning-block/',
                         'https://summitbrands.com/product/bathstone-cleaning-block/',
                         'https://summitbrands.com/product/poolstone-cleaning-block/',
                         'https://summitbrands.com/product/grillstone-cleaning-block/',
                         'https://summitbrands.com/product/grillstone-cleaning-block-starter-kit/',
                         'https://summitbrands.com/product/quiksand-drywall-sanding-block/',
                         'https://summitbrands.com/product/toiletstone-cleaning-block/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_detail)


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["brand"] = response.xpath('//h1[@class="brandColorHead hero-title"]/text()').get()
        price_list = re.findall(r"display_price&quot;:(.*?),", response.text)

        # items["current_price"] = self.price_fliter(response.xpath('//div[@class="BasicText Widget"]/text()').get())
        items["original_price"] = items["current_price"] = price_list[0]

        name = response.xpath('//h2[@class="product-subtitle"]/text()').get().strip()
        items["name"] = name

        cat_list = ['Home', items["brand"], name]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath('//meta[@name="description"]/@content').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = self.allowed_domains[0]

        # attr1_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[1]/text()').getall()
        # attr2_list = response.xpath('//div[@class="single-car-data"]/table//tr/td[2]/text()').getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a]+":"+attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath('//div[@class="woocommerce-product-gallery__image"]/a/@href').getall()
        items["images"] = images_list


        opt_name = response.xpath('//table[@class="variations"]//label/text()').getall()
        if not opt_name:
            items["sku_list"] = []
            # return
        else:
            opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
            opt_value = []
            value_temp = response.xpath('//td[@class="value"]//option/text()').getall()[1:]
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
            j = 0
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'Size':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                sku_info["current_price"] = price_list[j]
                sku_info["original_price"] = price_list[j]
                j += 1
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
