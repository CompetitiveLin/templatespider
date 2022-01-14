# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'respublica'
website_url = 'https://www.respublica.ru'

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
    allowed_domains = ['respublica.ru']
    start_urls = ['https://www.respublica.ru/']

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
        # category_urls = response.xpath("//li[@class='navPage-childList-item']/a/@href").getall()
        category_urls = ['/knigi', '/kantselyariya', '/dom', '/elektronika', '/hobbi-i-tvorchestvo', '/detyam', '/eda',
                         '/krasota', '/podarki']
        # category_urls = ['/podarki']
        for category_url in category_urls:
            category_url = website_url + category_url
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='photo-wrapper']/a/@href").getall()
        for detail_url in detail_url_list:
            detail_url = website_url + detail_url
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pages-next']/a/@href").get()
        if next_page_url:
            next_page_url = website_url + next_page_url
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//div[@class='price-current']/text()").get()
        price_new = price_new.replace('\n', '')
        price_new = price_new.replace(' ','')
        price_old = response.xpath("//div[@class='price-sale']/span[@class='price-old']/text()").get()
        if price_old:
            price_old = price_old.replace(' ','')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/font/font/text()").get()
        if name:
            name = name.replace('\n','')
            items["name"] = name.strip()
        else:
            name = response.xpath("//h1/text()").get()
            name = name.replace('\n', '')
            items["name"]=name.strip()

        cat_list = response.xpath('//ul[@itemscope]/li/span/a/span/text()').getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='desc']/text()").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        image_string = re.search(r'\(null,false,(.*?)"\)\);',response.text).group(1)
        image_list_String=re.findall(r',"(.*?)"',image_string)
        image_list = []
        for i in image_list_String:
            if i.find('thumb_')!=-1:
                i=i.replace('u002F','')
                i=i.replace('\\','/')
                i=i.replace('thumb','large')
                i=website_url+i
                image_list.append(i)
        items["images"] = image_list

        items["brand"] = response.xpath("//meta[@itemprop='brand']/@content").get()
        items["sku_list"] = []

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
