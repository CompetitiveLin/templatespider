# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
import random
import itertools
from scrapy.selector import Selector
import httpx
import demjson

from overseaSpider.util.utils import isLinux, filter_text
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from lxml import etree

website = 'bobux'

class BobuxSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['bobux.com']
    # start_urls = ['http://bobux.com/']
    domain_url = "https://www.bobux.com/".strip("/")
    users_agent = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",

        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",

        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    ]
    user_agent = random.choice(users_agent)
    headers_res = {"user-agent": user_agent}

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"]: 10
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(BobuxSpider, self).__init__(**kwargs)
        self.counts = 1
        setattr(self, 'author', "阿斌")

    is_debug = True
    custom_debug_settings = {
        # 'REDIRECT_ENABLED': False,
        # 'HTTPERROR_ALLOWED_CODES': [410],
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': False,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'DOWNLOAD_HANDLERS': {
        #     "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
        # },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        # maodian1
        url_list = [
                     "https://www.bobux.com/",
                     # "",
                       ]
        for url in url_list:
        #     print(url)
             yield scrapy.Request(
                 url=url,
                 callback=self.parse,
        #          callback=self.parse_detail,
                 meta={'h2': True},
        #          headers=self.headers,
             )

    def parse(self, response):
        url_list = response.xpath("//nav[contains(@class, 'main')]/ul/li//a/@href").getall()
        url_list = [u for u in url_list if "javascript:" not in u and "#" != u and "/" in u]
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta=response.meta,
                # headers=self.headers,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//ol[contains(@class, 'products')]/li/div/a[1]/@href").getall()
        # print(url_list)
        if url_list:
            url_list = [u for u in url_list if "javascript:" not in u and "#" != u]
            url_list = [response.urljoin(url) for url in url_list]
            breadcrumb_list = response.xpath("//div[contains(@class, 'breadcrumb')][1]/ul[1]/li/*//text()").getall()
            breadcrumb_list = [b for b in breadcrumb_list if b]
            meta = response.meta
            meta["breadcrumb_list"] = breadcrumb_list
            for url in url_list:
                # print(url)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta=meta,
                    # headers=self.headers,
                )

            if url_list:
                next_page_url = response.xpath("//li[contains(@class, 'next')]/a[contains(@title, 'Next')]/@href").get()
                if not next_page_url:
                    next_page_url = response.xpath("//li[contains(@class, 'next')]/a[contains(@class, 'next')]/@href").get()
                if not next_page_url:
                    next_page_url = response.xpath("//link[@rel='next']/@href").get()
                if next_page_url:
                    next_page_url = response.urljoin(next_page_url)
                    # print("下一页:"+next_page_url)
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse_list,
                        meta=response.meta,
                        # headers=self.headers,
                    )
        else:
            # url_list = response.xpath("//li[contains(@class, 'brand-item')]/a[contains(@class, 'item')]/@href").getall()
            # url_list = [u for u in url_list if "javascript:" not in u and "#" != u]
            # url_list = [response.urljoin(url) for url in url_list]
            # for url in url_list:
            #     # print(url)
            #     yield scrapy.Request(
            #         url=url,
            #         callback=self.parse_list,
            #     )
            pass

    def parse_detail(self, response):
        currency = "$"

        # stock = response.xpath("//link[@itemprop='availability']/@href").get()
        # stock = response.xpath("//meta[@itemprop='availability']/@content").get()
        # stock = response.xpath("//div[contains(@class, 'available')]/span[last()]/text()").get()
        stock = response.xpath("//meta[@property='product:availability']/@content").get()
        # stock = response.xpath("//div[contains(@class, 'pre-order success-color')]/text()").get()
        # stock = response.xpath("//div[@title='Availability']/span[last()]/text()").get()
        # stock = ""
        jsonConfig = re.findall("\"jsonConfig\":\s?(\{.*?\}),\n", response.text)
        if jsonConfig:
            sku_info_list = jsonConfig
        else:
            spConfig = re.findall("\"spConfig\":\s*(\{.*?\}),\n", response.text)
            sku_info_list = spConfig
            if not spConfig:
                jsonConfig = re.findall("\"jsonConfig\":\s*(\{.*?\}),\"jsonSwatchConfig", response.text)
                sku_info_list = jsonConfig
                if sku_info_list:
                    pass
                    # sku_info_list = [sku_info_list[0] + "}"]
                else:
                    jsonConfig = re.findall("\"spConfig\":\s*(\{.*?\}),\"gallerySwitchStrategy", response.text)
                    sku_info_list = jsonConfig

        if not stock or stock is None:
            stock = response.xpath("//span[@class='availability']/text()").getall()
            if stock:
                if "InStock" in stock or "instock" in stock or "In Stock" in stock or "in stock" in stock or "Instock" in stock:
                    stock = "InStock"
            else:
                stock = re.findall("\"availability\":\s*\"(.*?)\"", response.text)
                if stock:
                    stock1 = [s for s in stock if "out" in s]
                    if len(stock1) == len(stock):
                        stock = "out"
                    else:
                        stock = "InStock"
                else:
                    stock = response.xpath(
                        "//button[(@id[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'addtocart')]) or (@class[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'addtocart')])]")
                    if stock:
                        stock = "instock"
                    else:
                        stock = "out"
        if ("Out" not in stock and "out" not in stock and "oos" not in stock and "non" not in stock and "NOT" not in stock and "not" not in stock) or "DISPONIBILE" == stock:
            """详情页"""

            try:
                imgConfig = re.findall("\"data\":\s*(\[\{\"thumb\".*?\}]),", response.text)[0]
                imgConfig = json.loads(imgConfig)
            except:
                imgConfig = ""

            items = ShopItem()
            items["url"] = response.url

            original_price = response.xpath("//div[contains(@class, 'product-info-main') or contains(@class, 'product-info-price')]//span[(contains(@class, 'regular-price') or contains(@class, 'old-price') or contains(@class, 'price-was_price')) and (not(contains(@class, 'no-display')))]//span[contains(@data-price-type, 'oldPrice') or contains(@data-price-type, 'was_price')]/@data-price-amount").get()
            if not original_price:
                original_price = response.xpath(
                    "//div[contains(@class, 'product-info-price')]//span[(contains(@class, 'old-price') or (contains(@class, 'regular-price'))) and (not(contains(@style, 'display: none')))]//span[@data-price-type='oldPrice']/@data-price-amount").get()  # 第三种类型price
            if not original_price:
                original_price = response.xpath("//div[contains(@class, 'product-info-main') or contains(@class, 'product-info-price') or contains(@class, 'product-detail')]//span[(contains(@class, 'regular-price') or contains(@class, 'old-price') or contains(@class, 'price-was_price')) and (not(contains(@style, 'display: none')))]//span[contains(@data-price-type, 'oldPrice') or contains(@data-price-type, 'was_price')]/@data-price-amount").get()
            if not original_price:
                original_price = response.xpath("//div[(contains(@class, 'product-info-main')) or (contains(@class, 'product-info-price'))]//p[contains(@class, 'rrp')]//text()").get()
                if original_price:
                    original_price = original_price.replace("RRP", "").replace(currency, "").replace(",", "").strip()

            current_price = response.xpath(
                "//div[contains(@class, 'product-info-price')]//span[@data-price-type='finalPrice' or @data-price-type='basePrice']/@data-price-amount").get()
            if not current_price:
                current_price = response.xpath(
                    "//div[contains(@class, 'product-info-main')]//span[@data-price-type='finalPrice']/@data-price-amount").get()  # 第三种类型price
                if not current_price:
                    current_price = response.xpath("//div[contains(@class, 'product-top')]//span[@data-price-type='finalPrice']/@data-price-amount").get()
                if not current_price:
                    current_price = response.xpath("//meta[@property='product:price:amount']/@content").get()   # 万能
            if current_price:
                current_price = current_price.replace(currency, "").replace(",", "").strip()

            if original_price:
                if float(original_price) < float(current_price):
                    original_price = current_price
                else:
                    original_price = original_price
            else:
                original_price = current_price
            if not current_price:
                raise Exception("Gift Card? if not: Please enquire for asking price!.(if not, please modify the code!)")
            # if float(current_price) != 0:
            original_price = "{:.2f}".format(float(original_price))
            original_price1 = "{:.2f}".format(float(original_price))    # 用于拼接sku_price
            current_price = "{:.2f}".format(float(current_price))
            current_price1 = "{:.2f}".format(float(current_price))      # 用于拼接sku_price
            items["original_price"] = str(original_price).replace(",", "").replace(currency, "")
            items["current_price"] = str(current_price).replace(",", "").replace(currency, "")

            attr_list = response.xpath("//table[contains(@class, 'additional-attributes')]/tbody/tr")
            attributes = list()
            for attr in attr_list:
                key = " ".join(attr.xpath("./th//text()").getall()).replace("  ", " ").replace("\r", "").replace(
                    "\n", "").strip("\r\n\t ").strip(":").replace("  ", " ")
                value = " ".join(attr.xpath("./td//text()").getall()).replace("\r", "").replace("\n", "").replace(
                    "  ", " ").strip("\r\n\t ").replace("  ", " ")
                attributes.append(f"{key}: {value}")
            if attributes:
                items["attributes"] = attributes

            # brand = response.xpath("//div[contains(@class, 'product-brand-name')]/h3/text()").get()
            # brand = re.findall("\"brand\"\s*:\s*\{.*?name\"\s*:\s*\"(.*?)\"", response.text, re.S)
            # if not brand:
            #     brand = re.findall("\"brand\"\s*:\s*\"(.*?)\"", response.text)
            # brand = response.xpath("//span[contains(text(), 'Brand')]/following-sibling::span[1]/text()").get()
            brand = response.xpath("//meta[contains(@property, 'product:brand')]/@content").get()
            if brand and brand is not None:
                items["brand"] = brand.strip("\r\n\t ")
            else:
                items["brand"] = ""
            name = response.xpath(
                "//div[contains(@class, 'product-info-main')]//h1/span[contains(@class, 'base')]/text()").getall()
            if not name:
                name = response.xpath("//h1/span[contains(@class, 'base')]/text()").getall()
                if not name:
                    name = response.xpath("//meta[@property='og:title']/@content").getall()
            items["name"] = " ".join(name).strip().replace("\r", " ").replace("\n", " ").replace("\t", " ").replace("  ", " ").replace("  ", " ").strip("\r\n\t")

            description = response.xpath("//div[contains(@class, 'product attribute description')]/div[contains(@class, 'value')]//text()").getall()
            if not description:
                description = response.xpath("//meta[@property='og:description']/@content").getall()
            if description:
                items["description"] = re.sub("<.*?>", " ", filter_text(" ".join(description)).replace("  ", " ").replace("&lt;", "<").replace("&gt;", ">")).strip().replace("  ", " ")
            else:
                items["description"] = ""
            items["source"] = website
            # images_list = response.xpath("//div[@class='MagicScroll']/a/img/@src").getall()
            # images_list = [response.urljoin(i) for i in images_list]
            images_list = [i["full"] for i in imgConfig]
            if not images_list:
                images_list = response.xpath("//div[contains(@id, 'MagicToolboxSelectors')]/a/@href").getall()
                # print(images_list)
                if not images_list:
                    images_list = response.xpath("//div[contains(@id, 'mtImageContainer')]/div/a/@href").getall()


            images_list_test = list()
            for i in images_list:
                test = i
                # print(test)
                if ".gif" not in test and "placeholder/image" not in test and "coming_soon" not in test:
                    images_list_test.append(i)

            if images_list_test:
                items["images"] = images_list_test
                # if len(images_list_test) > 1:
                #     images_list_test[0], images_list_test[1] = images_list_test[1], images_list_test[0]

                meta = response.meta
                # Breadcrumb_list = ["breadcrumb_list"]   # maodian2
                Breadcrumb_list = meta["breadcrumb_list"]
                # Breadcrumb_list = response.xpath("//div[contains(@class, 'breadcrumb')]/ul/li//text()").getall()

                Breadcrumb_list = [b.strip() for b in Breadcrumb_list if b]
                if not Breadcrumb_list:
                    Breadcrumb_list = response.xpath("//div[contains(@class, 'breadcrumb')]/ul/li//text()").getall()
                    # Breadcrumb_list = meta["breadcrumb_list"]
                    if Breadcrumb_list:
                        Breadcrumb_list = [b.strip() for b in Breadcrumb_list if b]
                if not Breadcrumb_list:
                    items["cat"] = ""
                    items["detail_cat"] = ""
                else:
                    Breadcrumb_list2 = list(set(Breadcrumb_list))
                    Breadcrumb_list2.sort(key=Breadcrumb_list.index)
                    items["cat"] = Breadcrumb_list2[-1]
                    items["detail_cat"] = "/".join(Breadcrumb_list2).strip("/")

                sku_list = []
                if sku_info_list:
                    sku_info_list = json.loads(sku_info_list[0])
                    # print(sku_info_list)
                    try:
                        jsonSwatchConfig = re.findall("\"jsonSwatchConfig\":\s*(\{.*?\}),\n", response.text)[0]
                        # print(jsonSwatchConfig)
                        jsonSwatchConfig = json.loads(jsonSwatchConfig)
                    except:
                        try:
                            jsonSwatchConfig = re.findall("\"jsonSwatchConfig\":\s*(\{.*?\}),\"mediaCall", response.text)[0]
                            jsonSwatchConfig = json.loads(jsonSwatchConfig)
                            # print(jsonSwatchConfig)
                        except:
                            jsonSwatchConfig = ""

                    goods_data = {}
                    product_lis = []
                    for attr_key, attr_value in sku_info_list["attributes"].items():
                        # label = attr_value["label"].lower().strip()
                        for option in attr_value["options"]:
                            if option["products"]:
                                for product in option["products"]:
                                    if "sold out" not in option["label"] and "Sold Out" not in option["label"]:
                                        # print(product)
                                        product_lis.append(product)

                    product_list = list(set(product_lis))
                    product_list.sort(key=product_lis.index)
                    for pl in product_list:
                        goods_data[pl] = {}
                        goods_data[pl]["sku_type_list"] = {}

                    for attr_key, attr_value in sku_info_list["attributes"].items():
                        label = attr_value["label"].lower().strip()
                        code = attr_value["code"].lower().strip()
                        for option in attr_value["options"]:
                            if option["products"]:
                                for product in option["products"]:
                                    if product in goods_data:
                                        sku_type = label
                                        if not sku_type:
                                            sku_type = code
                                        try:
                                            sku_name = jsonSwatchConfig[attr_key][option["id"]]["label"]
                                        except:
                                            sku_name = option["label"]
                                        try:
                                            sku = sku_info_list["sku"][product]
                                        except:
                                            sku = product
                                        product_price = sku_info_list["optionPrices"][product]
                                        original_price = product_price["oldPrice"]["amount"]

                                        current_price = product_price["finalPrice"]["amount"]
                                        if original_price:
                                            if float(original_price) < float(current_price):
                                                original_price = current_price
                                            else:
                                                pass

                                        try:
                                            images = [i["full"] for i in sku_info_list["images"][product]]
                                        except:
                                            images = []

                                        goods_data[product]["sku_type_list"][sku_type] = sku_name
                                        goods_data[product]["sku"] = sku
                                        goods_data[product]["original_price"] = original_price
                                        goods_data[product]["current_price"] = current_price
                                        goods_data[product]["images"] = images
                    # print(goods_data)
                    for key, sku in goods_data.items():
                        try:
                            sku_stock = sku_info_list["stock"][key]
                            sku_stock = str(sku_stock)
                            # print(sku_stock)
                        except:
                            sku_stock = "Ture"
                        if sku_stock != "False" and sku_stock != "0":
                            # print(sku_stock)
                            sku_item = SkuItem()
                            original_price = sku["original_price"]
                            current_price = sku["current_price"]
                            original_price = "{:.2f}".format(float(original_price))
                            current_price = "{:.2f}".format(float(current_price))
                            sku_item["original_price"] = str(original_price).replace(",", "").replace(currency, "")
                            sku_item["current_price"] = str(current_price).replace(",", "").replace(currency, "")
                            ##     sku_item["inventory"] = sku["inventory"]
                            sku_item["sku"] = str(sku["sku"])
                            imgs = sku["images"]
                            #     imgs2 = list(set(imgs))
                            #     imgs2.sort(key=imgs.index)
                            sku_item["imgs"] = imgs
                            sku_item["url"] = response.url
                            attributes = SkuAttributesItem()
                            other = dict()
                            for sku_type, sku_name in sku["sku_type_list"].items():
                                if "size" == sku_type or "Size" == sku_type:
                                    attributes["size"] = sku_name
                                elif "colour" == sku_type or "color" == sku_type:
                                    attributes["colour"] = sku_name
                                else:
                                    other[sku_type] = sku_name
                            if other:
                                attributes["other"] = other
                            sku_item["attributes"] = attributes
                            sku_list.append(sku_item)
                else:
                    pass
                    # try:
                    #     optionConfig = re.findall("\"optionConfig\":\s*(\{.*?\}),\n", response.text)
                    #     if optionConfig:
                    #         optionConfig = json.loads(optionConfig[0])
                    #         outer = list()
                    #         for attr_key, attr_value in optionConfig.items():
                    #             keys = list(attr_value.keys())
                    #             inner = list()
                    #             for key in keys:
                    #                 goods_info = {}
                    #                 sku_data = attr_value[key]
                    #                 sku_name = sku_data["name"]
                    #                 sku_value = sku_data["type"]
                    #                 sku_old_price = sku_data["prices"]["oldPrice"]["amount"]
                    #                 sku_cur_price = sku_data["prices"]["finalPrice"]["amount"]
                    #
                    #                 goods_info["sku_name"] = sku_name
                    #                 goods_info["sku_value"] = sku_value
                    #                 goods_info["sku_old_price"] = sku_old_price
                    #                 goods_info["sku_cur_price"] = sku_cur_price
                    #                 inner.append(goods_info)
                    #             outer.append(inner)
                    #
                    #         for item in itertools.product(*outer):
                    #
                    #             sum_ori_price = 0
                    #             sum_cur_price = 0
                    #             sku_attr_list = []
                    #             for i, ite in enumerate(item):
                    #                 sum_ori_price += float(ite["sku_old_price"])
                    #                 sum_cur_price += float(ite["sku_cur_price"])
                    #                 sku_name = ite["sku_name"]
                    #                 sku_attr_list.append(sku_name)
                    #
                    #             sku_item = SkuItem()
                    #             original_price = "{:.2f}".format(float(sum_ori_price) + float(original_price1))
                    #             current_price = "{:.2f}".format(float(sum_cur_price) + float(current_price1))
                    #             sku_item["original_price"] = str(original_price).replace(",", "").replace(currency, "")
                    #             sku_item["current_price"] = str(current_price).replace(",", "").replace(currency, "")
                    #             imgs = []
                    #             imgs2 = list(set(imgs))
                    #             imgs2.sort(key=imgs.index)
                    #             sku_item["imgs"] = imgs
                    #             sku_item["url"] = response.url
                    #             attributes = SkuAttributesItem()
                    #             other = dict()
                    #             for i, sku_name in enumerate(sku_attr_list):
                    #                 sku_type = f"Option{str(i + 1)}"
                    #                 other[sku_type] = sku_name
                    #             if other:
                    #                 attributes["other"] = other
                    #             sku_item["attributes"] = attributes
                    #             sku_list.append(sku_item)
                    # except:
                    #     pass

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

                # detection_main(items=items, website=website, num=5, skulist=True, skulist_attributes=True)
                # item_check.check_item(items)
                print(items)
                # yield items
