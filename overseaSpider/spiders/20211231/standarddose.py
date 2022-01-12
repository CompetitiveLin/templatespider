# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from pprint import pprint
from collections import defaultdict

from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem

website = 'standarddose'

class standarddoseSpider(scrapy.Spider):
    name = website
    allowed_domains = ['standarddose.com']
    # start_urls = ['https://standarddose.com/']

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')

    def __init__(self, **kwargs):
        super(standarddoseSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "禄久")


    is_debug = True
    custom_debug_settings = {
        # 'MONGODB_SERVER': '127.0.0.1',
        # 'MONGODB_COLLECTION': 'fashionspider',
        # 'MONGODB_DB': 'fashions_pider',
        'MONGODB_COLLECTION': 'standarddose',
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'HTTPCACHE_ALWAYS_STORE': True,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',

    }

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


    def start_requests(self):
        url = "https://standarddose.com/collections/all-products"
        yield scrapy.Request(
            url=url,
        )

    def parse(self, response):
        for ir in range(0, 20):
            category_url = 'https://standarddose.com/collections/all-products/?page='
            category_url = category_url + str(ir)
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        detail_url_list = response.xpath('//h2[@class="ProductItem__Title Heading"]/a/@href').getall()
        if detail_url_list:
            print(f"当前商品列表页有{len(detail_url_list)}条数据")
            for detail_url in detail_url_list:
                detail_url = response.urljoin(detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    dont_filter=True
                )
        else:
            print(f"商品列表页无数据!:{response.url}")
            next_page_url = response.xpath('//a[@class="pagination-button pagination-button-next"]/@href').get()
            if next_page_url:
                next_page_url = response.urljoin(next_page_url)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_list,
                    dont_filter=True
                )
    def parse_detail(self, response):
        item = ShopItem()
        item["url"] = response.url
        item["source"] = website  # 来自哪个网站
        item["name"] = response.xpath("//div[@class = \"Product__InfoWrapper\"]//h1/text()").get()
        item["brand"] = response.xpath("//div[@class = \"Product__InfoWrapper\"]//h2/text()").get()
        item["detail_cat"] = 'All products' + '/' + item["name"]
        item["measurements"] = ['Height: None', 'Length: None', 'Depth: None', 'Weight: None']  # 规格尺寸
        item["original_price"] = self.price_fliter(response.xpath("//div[@class = \"Product__InfoWrapper\"]//span/text()").get())
        price = response.xpath("//span[@id = \"subscribepricemoney\"]/text()").get()
        if price:
            item["current_price"] = price
        else:
            item["current_price"] = item["original_price"]
        item["about"] = response.xpath("//div[@class = \"Product__InfoWrapper\"]//p/text()").get().replace("\n", "")  # 介绍文案
        item["url"] = response.url
        item["sku_list"] = []
        item["cat"] = response.xpath("//div[@class = \"shopify-section shopify-section--bordered\"]/section[@class = \"Product Product--large\"]/div[@class = \"Product__Wrapper\"]/nav[@class = \"breadcrumb\"]/span[2]/text()").get()
        # item["sales"] = scrapy.Field()  # 总销量
        # item["attributes"] = scrapy.Field()  # 商品属性材质列表
        # item["total_inventory"] = scrapy.Field()  # 总货存
        # item["care"] = scrapy.Field()  # 保养方式
        # item["sku_list"] = scrapy.Field()  # SkuItem's list
        des = response.xpath('//p[@class="descriptiontop"]/text()').get()
        if des:
            item["description"] = des.replace("\n", "").strip()  # 商品功能描述
        else:
            item["description"] = ''
        # item["video"] = scrapy.Field()  # 商品视频
        # color_list = response.xpath("//div[@class='flexcell--fill flexgrid flexgrid--wrap']/a/@data-attr-label").getall()
        # for color in color_list:

        #size_list = response.xpath("//div[@data-attr='size']/a/@data-value").getall()
        #variant_id = re.findall("(.*?).html?", response.url.split("/")[-1])[0]

        images_list = response.xpath("//div[@class = \"mainimagepdp Product__SlideItem Product__SlideItem--image Carousel__Cell is-selected\"]//img/@src").getall() # 商品图片
        item["images"] = [response.urljoin(images) for images in images_list]

        # dataLayer = re.findall("dataLayer.push\((.*?),\);</script>", response.text)
        # dataLayer = dataLayer[0] if dataLayer else None
        #
        # detail_data = re.findall("\[(.*?)\]", dataLayer)
        # detail_data = [data.strip() for data in detail_data if data.strip()][0]
        # json_detail_data = json.loads(detail_data)
        # print(json_detail_data)
        # current_color = json_detail_data["variant"].split(" ")[0]
        # item["brand"] = json_detail_data["brand"]
        # item["name"] = json_detail_data["name"]
        # item["cat"] = json_detail_data["category"]
        # item["detail_cat"] = json_detail_data["category"]  # 详细的类型
        # # current_color = response.xpath("//h1[@class='cell cell--span-3---small-down cell--col-pos-2---medium-up cell--span-3---medium-up cell--col-pos-3---xlarge cell--span-2---xlarge']/text()").get()

        status_list = list()
        status_list.append(item["url"])
        status_list.append(item["original_price"])
        status_list.append(item["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        item["id"] = md5(status.encode("utf8")).hexdigest()

        item["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        item["created"] = int(time.time())
        item["updated"] = int(time.time())
        item['is_deleted'] = 0

        print(item)
        # yield item

