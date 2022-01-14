# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from html.parser import HTMLParser
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'frontgate'

class FrontgateSpider(scrapy.Spider):
    name = website
    allowed_domains = ['frontgate.com']

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    }

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
        super(FrontgateSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "方尘")

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
        'DOWNLOAD_HANDLERS': {
            "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
        },
    }

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
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

    def start_requests(self):
        url = 'https://www.frontgate.com/'
        yield scrapy.Request(url=url, meta={'h2': True}, headers=self.headers, callback=self.parse)

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//li[@class='menuItem']/a/@href").getall()
        for category_url in category_urls:
            params = {
                'unbxdStart': '0',
                'rows': '30',
            }
            yield scrapy.FormRequest(
                url='https://www.frontgate.com' + category_url,
                method='get',
                formdata=params,
                meta={'h2': True, 'start': 0},
                headers=self.headers,
                callback=self.parse_list
            )

    def parse_list(self, response):
        """列表页"""
        json_text = re.search(r'<script>/\*(.*?)\*/</script>', response.text)
        if not json_text:
            return
        products = json.loads(json_text.group(1))['products']
        for product in products:
            yield scrapy.Request(
                url='https://www.frontgate.com' + product['targetURL'],
                callback=self.parse_detail,
                meta={'h2': True},
                headers=self.headers,
            )
        if products:
            start = int(response.meta.get('start')) + 30
            next_page_url = re.sub(r'\?unbxdStart=\d+', r'?unbxdStart={}'.format(start), response.url)
            yield scrapy.Request(
                url=next_page_url,
                meta={'h2': True, 'start': start},
                headers=self.headers,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        json_text = re.search(r'<span class="JSON nodisplay">.*?<script>/\*(.*?)\*/</script>', response.text, re.S)
        json_data = json.loads(json_text.group(1))['pageProduct']

        current_price = json_data['minPromoPrice']
        original_price = json_data['minListPrice']
        items["current_price"] = '$' + str(current_price)
        items["original_price"] = '$' + str(original_price) if original_price else items["current_price"]

        items["name"] = json_data['prodName']

        cat_list = response.xpath('//ul[@id="breadcrumbs_ul"]/li/a/text()').getall()
        cat_list = [cat.strip() for cat in cat_list if cat.strip()]
        items["detail_cat"] = '/'.join(cat_list)
        items["cat"] = json_data['categoryName']

        description = json_data['longDesc']
        description = HTMLParser().unescape(description)
        items["description"] = self.filter_text(self.filter_html_label(description))
        items["source"] = website

        images_text = re.search(r'(\{"@type":"ImageGallery".*})', response.text).group(1)
        items["images"] = [image['contentUrl'] for image in json.loads(images_text)['associatedMedia']]

        items["sku_list"] = self.parse_sku(json_data)

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
        print(items)
        yield items

    def parse_sku(self, json_data):
        attr_mapping = {attr['optionItemKey']: attr['optionName'].lower() for attr in json_data['definingAttributes']}
        variants = json_data['entitledItems']
        sku_list = list()
        for variant in variants:
            sku_info = SkuItem()
            sku_attr = SkuAttributesItem()
            if not variant.get('definingAttributes'):
                continue
            for option in variant['definingAttributes']:
                label = attr_mapping.get(option['optionItemKey'])
                label_value = option['displayName']
                if label == 'color' and label_value:
                    sku_attr["colour"] = label_value
                elif label == 'size' and label_value:
                    sku_attr["size"] = label_value
                elif label_value:
                    sku_attr["other"] = {'other': label_value}
            sku_info["current_price"] = '$' + str(variant['promoPrice'])
            sku_info["original_price"] = '$' + str(variant["listPrice"])
            sku_info["attributes"] = sku_attr
            sku_list.append(sku_info)
        return sku_list
