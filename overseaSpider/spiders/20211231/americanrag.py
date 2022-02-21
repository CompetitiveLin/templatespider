# -*- coding: utf-8 -*-
import re

import demjson
import requests
from overseaSpider.util.scriptdetection import detection_main
import time
import json
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
from scrapy.selector import Selector
from overseaSpider.util.item_check import check_item

from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem
from lxml import etree

website = 'americanrag'

class OverseaSpider(scrapy.Spider):
    name = website
    # start_urls = ['https://americanrag.com']


    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(OverseaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "彼得")
        self.headers = {
  'authority': 'www.galleryatthepark.org',
  'cache-control': 'max-age=0',
  'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'upgrade-insecure-requests': '1',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
  'sec-fetch-site': 'same-origin',
  'sec-fetch-mode': 'navigate',
  'sec-fetch-user': '?1',
  'sec-fetch-dest': 'document',
  'referer': 'https://www.galleryatthepark.org/adult-workshops',
  'accept-language': 'zh-CN,zh;q=0.9',
  'cookie': 'crumb=BXDuttEyu9JzOTk4MzhmYTFjMmE3YzYwODFjMjM5MTIwZDcyYzZm; ss_cvr=e00a7097-f852-40a8-b2ac-9946ede16818|1639894502220|1639894502220|1639900123364|2; ss_cvt=1639900123364',
  'if-none-match': 'W/"24b7d6786c7228b68090f816f328adbc--gzip"'
}


    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT': 5,  # 检测个数
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },

    }
    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F','\r\n\r\n','**','>>','\\n\\t\\t',', ','\\n        ',
                       '\\n\\t  ','\\xa0','>']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def start_requests(self):
        url_list = ["https://americanrag.com/mens",
                    "https://americanrag.com/womens",
                    "https://americanrag.com/homeware/fragrance-and-beauty",
                    "https://americanrag.com/homeware/decorative-items",
                    "https://americanrag.com/homeware/kitchen-and-dining",
                    "https://americanrag.com/homeware/furnishings",
                    ]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers=self.headers,
                meta={'url_list': url_list},
            )

    def parse(self, response):
        """主页"""
        # json_data = json.loads(response.text)
        # json_data = defaultdict(lambda: None, json_data)
        # url_list = response.xpath('//div[@class="sqs-block-content"]/div/figure/a/@href').getall()
        # url_list = [response.urljoin(url) for url in url_list]
        url_list = response.meta['url_list']
        product_num = response.xpath('//div[@class="c-product-listing__info"]/p[@class="c-product-listing__counts"]/text()[4]').get()
        # if product_num:
        #     product_num = product_num.split('/')[-1]
        #     product_num = product_num.split(')')[0]
        for url in url_list:
            # url = url + "?sortBy=newest&page=1"
            # print(url)
            # url = "https://www.romanchic.com/category/romanchic/100/"
            if product_num:
                url = url + "?size=" + product_num
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers,
            )

    def parse_list(self, response):
        """商品列表页"""
        # cat = response.url.split("=")[-1]
        # cat = cat.replace("%20"," ")
        detail_url_list = response.xpath('//div[@class="c-product-listing__products"]/div/a/@href').getall()
        # if not detail_url_list:
        #     detail_url_list = response.xpath("//div[@class='tovarphoto']/a/@href").getall()
        # detail_url_list = [response.urljoin(url) for url in detail_url_list]
        if detail_url_list:
            # print(f"当前商品列表页有{len(detail_url_list)}条数据")
            # detail_url = "https://www.saje.com/natural-mists/"
            for detail_url in detail_url_list:
                # if not detail_url == "https://www.saje.com/natural-mists/":
                detail_url = response.urljoin(detail_url)
                # detail_url = "https://www.christiansmattress.com/products/malouf-brushed-micro-fiber"
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    headers=self.headers,
                    # meta={'cat': cat},
                )


            # base_url = response.url.split("&start=")[0]
            # page_id = int(response.url.split("&start=")[1]) + 48
            # next_page_url = base_url + "&start=" + str(page_id)
            # if next_page_url:
            #     next_page_url = response.urljoin(next_page_url)
            #     # print("下一页:" + next_page_url)
            #     yield scrapy.Request(
            #         url=next_page_url,
            #         callback=self.parse_list,
            #         headers=self.headers,
            #     )
            # else:
            #   print(f"商品列表页无数据!:{response.url}")

            # next_page_url = response.xpath("//li[@class='page-item page-item--next']/a/@href").get()
            # if next_page_url:
            #     next_page_url = response.urljoin(next_page_url)
            #     # print("下一页:"+next_page_url)
            #     yield scrapy.Request(
            #         url=next_page_url,
            #         headers=self.headers,
            #         callback=self.parse_list,
            #     )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        brand = response.xpath('//h2[@data-testid="product-block-brand"]//text()').get()
        # if brand == "_":
        #     brand = ""
        # if not brand:
        #     brand = response.xpath("//div[@class='proLogo']/span/text()").get()
        # brand = brand.split(":")[0]
        # brand_list = re.findall('"brand":.*?name": "(.*?)"',response.text,re.S)
        # brand_list = re.findall('"brand":"(.*?)"', response.text)
        # brand = "".join(brand_list)
        # brand_all = response.xpath("//div[@class='productdetail product annex-cloud']/@data-productdetails").get()
        # brand = re.findall('"brand":"(.*?)","category"', brand_all)
        # print(brand)
        items["brand"] = brand
        # print(brand)
        name = response.xpath('//h2[@class="headings_productTitle__C3B3N"]/text()').get()
        name = name.replace("\n", "").replace("\xa0", "").replace("\u200b","").replace("    ","").replace("\u3000","")
        items["name"] = name

        original_price = response.xpath('//span[@data-testid="product-block-old_price"]/text()').get()
        current_price = response.xpath('//span[@data-testid="product-block-new_price"]/text()').get()
        if not original_price:
            original_price = response.xpath('//span[@data-testid="product-block-price"]/text()').get()
            current_price = response.xpath('//span[@data-testid="product-block-price"]/text()').get()

        detail_cat = []
        detail_cat_all = response.xpath('//div[@class="o-container u-pad-v-small u-pad-v@md"]/ul/li/a/text()').getall()
        for i in detail_cat_all:
            i = self.filter_text(i)
            # i.replace("\u3000","")
            detail_cat.append(i)
        s1 = "/"
        detail_cat = s1.join(detail_cat)
        items["detail_cat"] = detail_cat + "/" + name
        # items["detail_cat"] = detail_cat
        items["cat"] = name

        # detail_cat = response.meta['cat']
        # detail_cat = self.filter_text(detail_cat)
        # items["detail_cat"] = detail_cat
        # items["cat"] = detail_cat

        images_list = []
        images_list_1 = response.xpath('//div[@data-testid="pdp-main-images"]/img/@src').getall()
        # images_list_1 = re.findall("data-images='\[\"(.*?)\"\]'",response.text)
        # images_list_1 = images_list_1.split('\",\"')
        # if not images_list_1:
        #     # images_list_1 = response.xpath("//picture[@class='o-picture js-mainImage']/img/@src").getall()
        #     images_list_1 = re.findall("Square&quot;:&quot;(.*?)&quot;",response.text)
        for i in images_list_1:
            if not i in images_list:
                images_list.append(i)
        items["images"] = images_list

        items["url"] = response.url
        items["original_price"] = str(original_price)
        items["current_price"] = str(current_price)
        items["source"] = "americanrag"


        # judge = response.xpath("//div[@class='ec-base-button btnArea']/span//text()").getall()
        description = []
        description_1 = response.xpath('//div[@class="u-hidden@md-down c-product-details"]/details[@id="product-details"]/div//text()').getall()
        # if not description_1:
        #     description_1 = response.xpath('//div[@class="product-excerpt"]//text()').getall()
        for i in description_1:
            # if not ("SOLD OUT" == judge):
               i = self.filter_text(str(i)).replace("\\","")
               description.append(i)
        items["description"] = "".join(description)

        sku_list = list()
        size_list = []
        size_list_all = response.xpath('//fieldset[@class="u-mar-b-none c-variant__fieldset"]//span/text()').getall()
        if not size_list_all:
            size_list_all = response.xpath('//div[@class="o-layout o-layout--small u-mar-t-small"]//label[contains(@for,"size")]//span/text()').getall()
        for key in size_list_all:
            # if not "Choose an option" in key:
            key = self.filter_text(key)
            size_list.append(key)
        if size_list:
            for size in size_list:
                sku_item = SkuItem()
                sku_item["original_price"] = original_price
                sku_item["current_price"] = current_price
                sku_item["url"] = response.url
                sku_item["imgs"] = []
                attributes = SkuAttributesItem()
                # attributes["colour"] = color
                attributes["size"] = size
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)
        else:
            sku_item = SkuItem()
            sku_item["original_price"] = original_price
            sku_item["current_price"] = current_price
            sku_item["url"] = response.url
            sku_item["imgs"] = []

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
        #                skulist_attributes=True)

        # print(items)
        # check_item(items)
        yield items
