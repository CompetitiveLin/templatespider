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

website = 'ottica-roma'
website_url = 'https://www.ottica-roma.net'

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
    allowed_domains = ['ottica-roma.net']
    start_urls = ['https://www.ottica-roma.net/']

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
        category_urls = response.xpath("//ul[@class='sub-menu']/li[@id]/a/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='woo-entry-image-swap woo-entry-image clr']/a[1]/@href").getall()
        # detail_url_list =[
        #     'https://www.ottica-roma.net/prodotto/optox-opto-gel-a-integratore/',
        #     'https://www.ottica-roma.net/prodotto/soleko-queens-solitaire-lenti-colorate-graduabili-trimestrali/',
        #     'https://www.ottica-roma.net/prodotto/1-day-oasys-for-astigmatism-acuvue-30-lenti-a-contatto/'
        # ]
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@class='next page-numbers']/@href").get()
        if next_page_url:
            next_page_url = website_url + next_page_url
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        price_list = response.xpath("//p[@class='price']//span[@class='woocommerce-Price-amount amount']/bdi/text()").getall()
        isSale = response.xpath("//p[@class='price']/text()").get()
        if not price_list:
            return
        for i in range(len(price_list)):
            price_list[i] = price_list[i].replace('.', '')
            price_list[i]=price_list[i].replace(',','.')
        if len(price_list)>1:
            if isSale!=" ":
                price_high = price_list[1]
                price_low = price_list[0]
                price_new = price_low
                items["original_price"] = price_new
                items["current_price"] = price_new
            else:
                price_old = price_list[0]
                price_new = price_list[1]
                items["original_price"] = price_old
                items["current_price"] = price_new
        else:
            items["original_price"] = price_list[0]
            items["current_price"] = price_list[0]

        name = response.xpath("//h2[@itemprop='name']/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ol/li/a//span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@data-elementor-type]").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//div[@data-thumb]/a/@href").getall()
        items["images"] = images_list
        sku_string = response.xpath("//form[@data-product_variations]/@data-product_variations").get()
        if not sku_string:
            items["sku_list"] = []
        else:
            sku_json = json.loads(sku_string)
            attribute_json = sku_json[0]['attributes']
            img_dict = dict()
            price_old_dict = dict()
            price_new_dict = dict()
            opt_name = []
            opt_value = []
            major = ''
            for i in attribute_json:
                index = i.find("_")
                opt_name.append(i[index+1:])
                if attribute_json[i]:
                    major=i[index+1:]
            if major:
                for i in sku_json:
                    price_new_dict[i['attributes']['attribute_'+major]]='{:.2f}'.format(i['display_price'])
                    price_old_dict[i['attributes']['attribute_'+major]]='{:.2f}'.format(i['display_regular_price'])
                    img_dict[i['attributes']['attribute_'+major]]=i['image']['url']
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//tbody/tr["+str(i+1)+"]/td[@class='value']//option[position()>1]/@value").getall()
                if value_temp:
                    opt_value.append(value_temp)
            attrs_list = []
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'colore':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                if major:
                    for attr in attrs.items():
                        if attr[0]== major:
                            sku_info["current_price"] = str(price_new_dict[attr[1]])
                            sku_info["original_price"] = str(price_old_dict[attr[1]])
                            img_list=[]
                            img_tmp = img_dict[attr[1]]
                            img_list.append(img_tmp)
                            sku_info["imgs"] = img_list
                else:
                    sku_info["current_price"] = items["current_price"]
                    sku_info["original_price"] = items["original_price"]
                    img_list = []
                    img_tmp = images_list[0]
                    img_list.append(img_tmp)
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
        detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
