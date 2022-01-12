# -*- coding: utf-8 -*-
import re
import json
import time

# import parse
import scrapy
import requests
from hashlib import md5

# from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.utils import isLinux
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main

website = '119corbo'

class A119corboSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://119corbo.com/collections/ann-demeulemeester']
    # start_urls = ['http://https://119corbo.com/collections/ann-demeulemeester/']
    headers = {
        'authority': '119corbo.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
        'sec-ch-ua-mobile': '?0',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cookie': 'secure_customer_sig=; cart_currency=CAD; _orig_referrer=; _landing_page=%2Fcollections%2Fnew-arrivals%2Fproducts%2Fblack-pants; _y=9b507f41-e5fa-4c71-9f11-e01c3ba091b0; _shopify_y=9b507f41-e5fa-4c71-9f11-e01c3ba091b0; cart=f0d4d02a9c0d2c62bc52775a04431881; cart_ts=1629702593; cart_sig=784bdf6674d148c3dbcc931bb84aa9c8; cart_ver=gcp-us-east1%3A1; _ga=GA1.2.1462557938.1629702594; _gid=GA1.2.1404389710.1629702594; _fbp=fb.1.1629702594740.1166760022; _shg_user_id=581b16f2-b044-4aae-9f95-d155ca1d38fd; locksmith-params=%7B%22geonames_feature_ids%22%3A%5B1814991%2C6255147%5D%2C%22geonames_feature_ids%3Asignature%22%3A%229ec5935d687b578ced4c91dc5709e86020fe7693dc24ef0de8313fa51f8a726d%22%7D; _s=3148f811-cc7d-4f01-a42e-bf6222b8474f; _shopify_s=3148f811-cc7d-4f01-a42e-bf6222b8474f; _shopify_sa_p=; shopify_pay_redirect=pending; _shg_session_id=ba7ee250-598e-45b4-b58d-ae2e24f9773a; _shopify_sa_t=2021-08-24T01%3A56%3A59.714Z; __kla_id=eyIkcmVmZXJyZXIiOnsidHMiOjE2Mjk3MDI1OTgsInZhbHVlIjoiIiwiZmlyc3RfcGFnZSI6Imh0dHBzOi8vMTE5Y29yYm8uY29tL2NvbGxlY3Rpb25zL25ldy1hcnJpdmFscy9wcm9kdWN0cy9ibGFjay1wYW50cyJ9LCIkbGFzdF9yZWZlcnJlciI6eyJ0cyI6MTYyOTc3MDIyMiwidmFsdWUiOiIiLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly8xMTljb3Jiby5jb20vY29sbGVjdGlvbnMvbmV3LWFycml2YWxzL3Byb2R1Y3RzL2dhbHlhLXRvcC1ibGFjayJ9fQ==',
    }

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            custom_debug_settings['CLOSESPIDER_ITEMCOUNT'] = 15
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(A119corboSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "肥鹅")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        url_list = [
            'https://119corbo.com/collections'
        ]
        for url in url_list:
            #print(url)
            yield scrapy.Request(
                url=url,
                headers=self.headers
            )

    def parse(self, response):
        url_list = response.xpath("//div[@class='subNavWrapper desktopSubNavWrapper foursubmenu']/div[position()>1]/ul/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            #print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath('//div[@class="product-card__image-with-placeholder-wrapper"]/a/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            #print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                headers=self.headers
            )

    def parse_detail(self, response):
        if response.xpath("//div[@class='infoBar productTitle']/text()"):
            """详情页"""
            items = ShopItem()
            items["url"] = response.url
            # price = re.findall("", response.text)[0]
            original_price = ''
            current_price = ''
            if response.xpath("//div[@class='bottomFormPart flex']//div[@class='price__sale']//s[@class='price-item price-item--regular']/text()").get():
                original_price = self.filter_html_label(response.xpath("//div[@class='bottomFormPart flex']//div[@class='price__sale']//s[@class='price-item price-item--regular']/text()").get()).split(' CAD')[0][1:]
                original_price = original_price.replace(',','')
            if response.xpath("//div[@class='bottomFormPart flex']//div[@class='price__sale']//span[@class='price-item price-item--sale main-item-price']/text()").get():
                current_price = self.filter_html_label(response.xpath("//div[@class='bottomFormPart flex']//div[@class='price__sale']//span[@class='price-item price-item--sale main-item-price']/text()").get()).split(' CAD')[0][1:]
                current_price = current_price.replace(',','')
            items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
            items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
            items["brand"] = self.filter_html_label(response.xpath("//div[@class='infoBar vendorName']/a/text()").get())
            items["name"] = self.filter_html_label(response.xpath("//div[@class='infoBar productTitle']/text()").get())
            attributes = list()
            attribute = response.xpath("//div[@class='custom-field custom-field__details custom-field__type--text']//div[@class='custom-field--value metaInfo']//text()").getall()
            for j in attribute:
                j = self.filter_html_label(j)
                if j:
                    attributes.append(self.filter_html_label(j))
            items["attributes"] = attributes
            items["description"] = self.filter_html_label(response.xpath("//div[@class='infoBarContainer flex']/div[@class='right']/div/p[1]/span/text()").get())
            if not items["description"]:
                items["description"] = self.filter_html_label(response.xpath("//div[@class='infoBarContainer flex']/div[@class='right']/div//span/text()").get())
            items["source"] = website
            images_list = list()
            images_lists = response.xpath("//div[@class=' grid__item productImagesBoxCustom secondSetOfProductImages ' or @class=' grid__item firstProductImage productImagesBoxCustom  ']/img/@src").getall()
            for i in images_lists:
                images_list.append('https:'+i)
            items["images"] = images_list
            # Breadcrumb_list = response.xpath("").getall()
            items["cat"] = items['name']
            if items['name']:
                items["detail_cat"] = 'Home/'+items['name']
            else:
                items["detail_cat"] = 'Home'

            sku_list = list()
            original_sku_list = list()
            size_colour = response.xpath('//div[@class="selectionWrapper"]/select/option/text()').getall()
            for i in size_colour:
                i = self.filter_html_label(i.split('- Sold out')[0])
                sku = SkuItem()
                sku["original_price"] = items["original_price"]
                sku["current_price"] = items["current_price"]
                imgs = list()
                sku["imgs"] = imgs
                sku["url"] = response.url
                attributes = SkuAttributesItem()
                if '/' in i:
                    attributes["colour"] = self.filter_html_label(i.split('/')[1])
                    attributes["size"] = self.filter_html_label(i.split('/')[0])
                else:
                    attributes["size"] = self.filter_html_label(i)
                sku["attributes"] = attributes
                original_sku_list.append(sku)

            for sku in original_sku_list:
                sku_item = SkuItem()
                sku_item["original_price"] = items["original_price"]
                sku_item["current_price"] = items["current_price"]
                #sku_item["inventory"] = sku["inventory"]
                #sku_item["sku"] = sku["sku"]
                imgs = list()
                sku_item["imgs"] = imgs
                # sku_item["url"] = response.url
                # sku_item["sku"] = sku
                attributes = SkuAttributesItem()
                if 'colour' in sku["attributes"].keys():
                    attributes["colour"] = sku["attributes"]["colour"]
                attributes["size"] = sku["attributes"]["size"]
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)

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
            # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
            #                 skulist_attributes=True)
            print(items)
            # item_check.check_item(items)
            # yield items

    def filter_html_label(self, text):
        if text:
            html_labels_zhushi = re.findall('(<!--[\s\S]*?-->)', text)  # 注释
            if html_labels_zhushi:
                for zhushi in html_labels_zhushi:
                    text = text.replace(zhushi, '')
            html_labels = re.findall(r'<[^>]+>', text)  # html标签
            for h in html_labels:
                text = text.replace(h, '')
            text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('\xa0', '').replace('&gt;',
                                                                                                          '/').replace(
                '  ',
                '').strip()
            return text
        else:
            return None
