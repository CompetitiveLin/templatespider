# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from pprint import pprint
from collections import defaultdict
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'bluenile'
#100....pause

class BluenileSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['bluefly.com']
    # start_urls = ['https://www.bluenile.com/']

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')

    def __init__(self, **kwargs):
        super(BluenileSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "泽塔")

    is_debug = True
    custom_debug_settings = {
        # 'MONGODB_SERVER': '127.0.0.1',
        # 'MONGODB_DB': 'fashionspider',
        # 'MONGODB_COLLECTION': 'fashions_pider',
        'MONGODB_COLLECTION': 'bluenile',
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60,  # 秒
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

    def start_requests(self):
        url = "https://www.bluenile.com/"
        yield scrapy.Request(
            url=url,
        )

    def parse(self, response):
        """主页"""
        # json_data = json.loads(response.text)
        url_list = ["https://www.bluenile.com/api/public/diamond-search-grid/v2?pageSize=24&_=1626334040546&unlimitedPaging=true&sortDirection=asc&sortColumn=default&shape=RD&maxDateType=MANUFACTURING_REQUIRED&isQuickShip=false&hasVisualization=false&isFiltersExpanded=false&astorFilterActive=false&country=USA&language=en-us&currency=USD&productSet=BN&startIndex=0",
                    "https://www.bluenile.com/api/public/build-your-own-ring/setting-search?country=USA&language=en-us&productSet=BN&currency=USD&pageId=BYOR%20Setting%20Search&sort=RBS&minPrice=240&maxPrice=14990&pageSize=24&startIndex=0",
                    "https://www.bluenile.com/api/public/catalog?country=USA&language=en-us&productSet=BN&currency=USD&pageId=Wedding%20Rings%20Catalog&sort=BS&minPrice=128&maxPrice=34990&pageSize=24&startIndex=0",
                    "https://www.bluenile.com/api/public/catalog?country=USA&language=en-us&productSet=BN&currency=USD&pageId=Jewelry%20Catalog&sort=RBS&minPrice=40&maxPrice=120000&pageSize=24&startIndex=0",
                    ]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """商品列表页JSON TYPE"""
        json_data = json.loads(response.text)
        json_data = defaultdict(lambda: None, json_data)
        #judge_diamond_or_ring
        if "recommendedCountRaw" in json_data:
            diamond_details_url_results = json_data["results"]
            for i in diamond_details_url_results:
                if "detailsPageUrl" in i:
                    diamond_details_url_list = list()
                    diamond_details_url_list.append(i["detailsPageUrl"])
                    #***NEW***
                    diamond_details_url_list = [index.split("/")[-1] for index in diamond_details_url_list]
                    url_id = diamond_details_url_list[0]
                    #diamond_details_url = f"https://www.bluenile.com/api/public/recently-viewed-slider?currency=USD&country=USA&language=en-us&excludeItemId={url_id}"
                    diamond_details_url = f"https://www.bluenile.com/diamond-details/{url_id}"
                    yield scrapy.Request(
                        url=diamond_details_url,
                        callback=self.parse_detail,
                        meta={"url_id": url_id}
                    )

                if json_data["results"]:
                    base_url = response.url.split("&startIndex=")[0]
                    page_id = int(response.url.split("&startIndex=")[1]) + 24
                    next_page_url = base_url + "&startIndex=" + str(page_id)
                    if next_page_url:
                        # next_page_url = response.urljoin(next_page_url)
                        yield scrapy.Request(
                            url=next_page_url,
                            callback=self.parse_list,
                        )
        else:
            json_data_ring = json.loads(response.text)
            json_data_ring = defaultdict(lambda: None, json_data_ring)
            products_details_list = json_data_ring["results"]
            for i in products_details_list:
                name = i["name"]
                brand = "bluenile"
                url = i["url"]
                category = i["transactionProduct"]["category"]
                if "price" in i:
                    original_price = i["price"].replace(",", "")
                else:
                    original_price = "$" + i["priceRounded"]
                if i["retailPrice"]:
                    current_price = i["retailPrice"]
                else:
                    current_price = original_price
                description = i["description"]
                images_list = list()
                if "v3_catprod_lrg" in i["image"]:
                    image = i["image"].replace("v3_catprod_lrg", "phab_detailmain")
                if "v3_catprod_lrg" in i["secondImage"]:
                    secondImage = i["secondImage"].replace("v3_catprod_lrg", "phab_detailmain")
                images_list.append(image)
                images_list.append(secondImage)
                sku_list = list()
                if "relatedOffers" in i:
                    sku_detail_info = i["relatedOffers"]
                    #print(sku_detail_info)
                    if sku_detail_info:
                        sku_info_list = sku_detail_info["metals"]
                        #print(sku_info_list)
                        for j in sku_info_list:
                            sku_info = SkuItem()
                            sku_attr = SkuAttributesItem()
                            sku_id = j["offerId"]
                            sku_info["sku"] = sku_id

                            color = j["color"]
                            sku_attr["colour"] = color

                            icon = j["icon"]
                            sku_attr["other"] = icon

                            sku_current_price = current_price
                            sku_info["current_price"] = sku_current_price
                            original_price = original_price
                            sku_info["original_price"] = original_price

                            sku_info["attributes"] = sku_attr
                            sku_list.append(sku_info)
                    # else:
                    #     print("ERROR 4 NO METALS!!!!!!")

                items = ShopItem()
                items["url"] = url
                items["name"] = name
                items["brand"] = brand
                items["cat"] = category.replace("::", " ").replace(" ","/")
                items["detail_cat"] = category.replace("::", " ").replace(" ","/")
                items["current_price"] = current_price
                items["original_price"] = original_price
                items["description"] = description
                items["source"] = website
                items["images"] = images_list
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

                print(items)
                yield items

            if json_data_ring["results"]:
                base_url = response.url.split("&startIndex=")[0]
                page_id = int(response.url.split("&startIndex=")[1]) + 24
                next_page_url = base_url + "&startIndex=" + str(page_id)
                if next_page_url:
                    # next_page_url = response.urljoin(next_page_url)
                    yield scrapy.Request(
                        url=next_page_url,
                        callback=self.parse_list,
                    )

    def parse_detail(self, response):
        """详情页JSON TYPE"""
        # DIAMOND DETAILS
        html_json_data = response.xpath("//script[@type='application/json' and contains(text(),'titleArea')]").get()
        json_data = re.findall("{.*}}", html_json_data)
        json_data = json.loads(json_data[0])
        json_data = defaultdict(lambda: None, json_data)
        #print(f"TEST JSON:{json_data}")

        product_id = response.meta["url_id"]
        name = json_data["titleArea"]["title"]
        url = response.url
        cat = "diamonds"
        detail_cat = "diamonds"
        brand = "bluenile"
        description = json_data["titleArea"]["description"]
        current_price = json_data["price"]["price"]
        original_price = json_data["price"]["strikethroughPrice"]
        images_list = list()
        images_info_list_a = json_data["details"][0]["images"]
        for image in images_info_list_a:
            images_list.append(image["url"])
        images_info_list_b = json_data["imageViewer"]["slides"]
        for image in images_info_list_b:
            img_dir_info = image["slideData"]
            if "url" in img_dir_info:
                images_list.append(img_dir_info["url"])
        #print(f"TEST666:{images_list}")
        sku_list = list()

        items = ShopItem()
        items["id"] = product_id
        items["name"] = name
        items["url"] = url
        items["cat"] = cat
        items["detail_cat"] = detail_cat
        items["brand"] = brand
        items["description"] = description
        items["source"] = website
        items["current_price"] = current_price
        items["original_price"] = original_price
        items["images"] = images_list
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

        print(items)
        # yield items

