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

website = 'superherostuff'
website_url = 'https://superherostuff.com'

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
    allowed_domains = ['superherostuff.com']
    start_urls = ['https://superherostuff.com/']

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
        category_urls = ['/mens-merchandise.html',
                         '/women-merchandise.html',
                         '/superhero-kids-merchandise.html',
                         '/superherostuff-exclusives.html']
        for category_url in category_urls:
            category_url = website_url + category_url
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@data-equalizer='product-cards']/a/@href").getall()
        for detail_url in detail_url_list:
            detail_url = website_url + detail_url
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@title='Go to next page']/@href").get()
        if next_page_url:
            next_page_url = website_url + next_page_url
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//h3[@class='product-price']/span[1]/text()").get()
        price_new = price_new.replace("$",'')
        price_old = response.xpath("//h3[@class='product-price']/span[2]/text()").get()
        if price_old:
            price_old = price_old.replace("Reg.$",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='details details--categories']//li/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            cat_list = [cat.replace(",",'') for cat in cat_list]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='product-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website
        brand = response.xpath("//ul[@class='details details--brands']/li/text()").get()
        brand = brand.replace(",",'')
        brand = brand.strip()
        items['brand']= brand
        images_list = response.xpath("//div[@class='slide slide--product-gallery']/a/img/@src").getall()
        if images_list:
            items["images"] = images_list
        else:
            images_list = response.xpath("//div[@class='single-product__photo']/a/img/@src").getall()
            items["images"] = images_list
        issku = response.xpath("//div[@class='select-wrapper']/select[@id='prd-child']").get()
        if not issku:
            items["sku_list"] = []
        else:
            opt_name = ['size']
            opt_value = []
            size_dict_new = dict()
            size_dict_old = dict()
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='select-wrapper']/select[@id='prd-child']/option[not(@disabled)]/text()").getall()

                value_price_new =  response.xpath("//div[@class='select-wrapper']/select[@id='prd-child']/option[not(@disabled)]/@data-sale-price").getall()
                value_price_old = response.xpath("//div[@class='select-wrapper']/select[@id='prd-child']/option[not(@disabled)]/@data-price").getall()
                if value_temp:
                    opt_value.append(value_temp)
                for v in range(len(value_temp)):
                    value_temp[v] = value_temp[v].replace('\n','')
                    if price_old:
                        size_dict_old[value_temp[v]] = value_price_old[v]
                        size_dict_new[value_temp[v]] = value_price_new[v]
                    else:
                        size_dict_new[value_temp[v]] = value_price_old[v]
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
                    if attr[0] == 'size':
                        sku_attr["size"] = attr[1]

                if price_old:
                    sku_info["current_price"] = str(size_dict_new[sku_attr['size']])
                    sku_info["original_price"] = str(size_dict_old[sku_attr['size']])
                else:
                    sku_info["current_price"] = str(size_dict_new[sku_attr['size']])
                    sku_info["original_price"] = str(size_dict_new[sku_attr['size']])
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
