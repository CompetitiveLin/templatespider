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

website = 'baby-koo'


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
    allowed_domains = ['baby-koo.com']
    start_urls = ['https://www.baby-koo.com/']

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
        category_urls = ['https://www.baby-koo.com/nursery-furniture-store.html',
                         'https://www.baby-koo.com/baby-feeding.html',
                         'https://www.baby-koo.com/baby-bath.html',
                         'https://www.baby-koo.com/baby-gear-boston.html',
                         'https://www.baby-koo.com/baby-and-kids-toys.html',
                         'https://www.baby-koo.com/baby-and-kids-clothing.html',
                         'https://www.baby-koo.com/for-mom.html',
                         'https://www.baby-koo.com/baby-gifts-en.html']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='ty-column3']//div[@class='ty-grid-list__item-name']/a/@href").getall()
        for detail_url in detail_url_list:
            if detail_url != 'https://www.baby-koo.com/personalized-music-box.html':
                yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@class='ty-pagination__item ty-pagination__btn ty-pagination__next cm-history cm-ajax ty-pagination__right-arrow']/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//div[@class='ty-product-block__price-actual']//span[@class='ty-price-num' and @id]/text()").get()
        price_old = response.xpath("//div[@class='ty-product-prices']//span[@class='ty-strike']//span[@class='ty-list-price ty-nowrap' and @id]/text()").get()
        if price_old:
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//div[@class='ty-breadcrumbs clearfix']/a/text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@id='content_description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//div[@class='ty-product-thumbnails ty-center cm-image-gallery']/a/img/@src").getall()
        for i in range(len(images_list)):
            index1 = images_list[i].find("thumbnails")
            index2 = images_list[i].find("detailed")
            images_list[i] = images_list[i][:index1]+images_list[i][index2:]
        if not images_list:
            images_list = response.xpath("//div[@class='ty-product-img cm-preview-wrapper']/a/@href").getall()
        items["images"] = images_list
        brand = response.xpath("//div[@class='brand']//a/text()").get()
        if brand:
            items["brand"] = brand
        else:
            items["brand"] = ''

        opt_name = response.xpath("//div[@class='cm-picker-product-options ty-product-options']/div/label/text()").getall()
        if not opt_name:
            items["sku_list"] = []
        else:
            opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
            opt_value = []
            img_dict = dict()
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='cm-picker-product-options ty-product-options']/div["+str(i+1)+"]//option/text()").getall()
                value_img = response.xpath("//div[@class='cm-picker-product-options ty-product-options']/div["+str(i+1)+"]/div/img/@src").getall()
                for v in range(len(value_temp)):
                    value_temp[v]=value_temp[v].replace("\n",'')
                    value_temp[v]=value_temp[v].strip()
                if value_img:
                    if len(value_temp)!=len(value_img):
                        return
                    else:
                        for v in range(len(value_temp)):
                            index1 = value_img[i].find("thumbnails")
                            index2 = value_img[i].find("detailed")
                            value_img[i] = value_img[i][:index1] + value_img[i][index2:]
                            img_dict[value_temp[v]]=value_img[i]
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
                img_list = []
                for attr in attrs.items():
                    if len(img_dict)!=0:
                        img_list.append(img_dict[attr[1]])
                    if attr[0].find("Size")!=-1:
                        sku_attr["size"] = attr[1]
                    elif attr[0].find("Color")!=-1:
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["attributes"] = sku_attr

                if len(img_list)!=0:
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
