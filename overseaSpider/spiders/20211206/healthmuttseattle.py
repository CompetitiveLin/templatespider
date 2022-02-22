# -*- coding: utf-8 -*-
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from bs4 import BeautifulSoup

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'healthmuttseattle'
website_url = 'https://www.healthmuttseattle.com'

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
    allowed_domains = ['healthmuttseattle.com']
    start_urls = ['https://www.healthmuttseattle.com/']

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
        category_urls = [
            'https://www.healthmuttseattle.com/products/list/?categories=00040003',
            'https://www.healthmuttseattle.com/products/list/?categories=0003000D',
            'https://www.healthmuttseattle.com/products/list/?categories=00040009&categories=0003000B'
        ]
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='prdct-thmb-vertic']/a/@href").getall()
        for detail_url in detail_url_list:
            detail_url = website_url + detail_url
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        isNext = response.xpath("//a[@data-el-querystring-key][last()]/text()").get()
        if isNext=="Next":
            next_page_url = response.xpath("//a[@data-el-querystring-key][last()]/@href").get()
            if next_page_url:
                next_page_url = website_url + next_page_url
                yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//span[@class='current-price']/text()").get()
        price = price.replace("$",'')
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        items["cat"] = ''
        items["detail_cat"] = ''

        description = response.xpath("//div[@id='description']/div/div[@class='col-sm-7']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list_1 = response.xpath("//div[@class='thumb-item']/img/@src").getall()
        images_list_2 = response.xpath("//div[@class='thumb-item']/img/@data-lazy").getall()

        images_list = []
        for img1 in images_list_1:
            images_list.append(img1)
        for img2 in images_list_2:
            images_list.append(img2)
        items["images"] = images_list

        isOP = response.xpath("//div[@class='input-group']/div/label/a/text()").getall()
        if not isOP:
            items["sku_list"] = []
        else:
            opt_name = ['size']
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            size_dict = dict()
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='input-group']/div/label/a/text()").getall()
                value_url = response.xpath("//div[@class='input-group']/div/label/a/@href").getall()
                for i in range(len(value_temp)):
                    size_dict[value_temp[i]]=website_url + value_url[i]
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

                for attr in attrs.items():
                    if attr[0] == 'size':
                        sku_attr["size"] = attr[1]

                url = size_dict[sku_attr["size"]]
                url = url.strip()
                payload = {}
                headers = {
                    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                    'Cookie': 'csrftoken=4FGTGGZuI9YedHGdllITGyFAJmMxcWjrFzLutTzxu1O3YHq6s47mW9Xco4030j8s; sessionid=tzvz3h2e1x5s7ktqns2ifcs07wbzwjvz'
                }
                response0 = requests.request("GET", url,headers=headers, data=payload)
                soup = BeautifulSoup(response0.text,'lxml')
                price_list = soup.select(".current-price")
                for j in price_list:
                    price = j.string
                price = price.replace('$','')
                sku_info["current_price"] = price
                sku_info["original_price"] = price
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
