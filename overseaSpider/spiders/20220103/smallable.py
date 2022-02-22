# -*- coding: utf-8 -*-
import re
import time
import json
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
from lxml import etree
from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem

website = 'smallable'

class SmallableSpider(scrapy.Spider):
    name = website
    # start_urls = ['https://www.smallable.com/en/']


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
        super(SmallableSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "泽塔")

        self.headers = {
            'authority': 'www.smallable.com',
            'cache-control': 'max-age=0',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'referer': 'https://www.smallable.com/en/',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': 'SML_PHPSESSID=g2gqi416p3h42prbc3fd9uvu7c; hl=en; device_view=full; info_popin_open=1; _ga=GA1.2.343643619.1627031312; _gid=GA1.2.2124814206.1627031312; didomi_token=eyJ1c2VyX2lkIjoiMTdhZDI5ZjktODczZS02YmNiLWFiYTEtMjIzOTMyYjkyMjA5IiwiY3JlYXRlZCI6IjIwMjEtMDctMjNUMDk6MDg6MzQuMzQ1WiIsInVwZGF0ZWQiOiIyMDIxLTA3LTIzVDA5OjA4OjM0LjM0NVoiLCJ2ZXJzaW9uIjpudWxsfQ==; etuix=r_Fz93NVmVCA_yBDQfKRtzyh5oVtMJyDOfrvc21NHV7bYkM8VJGSQA--; _dc_gtm_UA-72158538-1=1; uptiTool=2361627031314738.1627102788.none|none|direct|none|none|none; sm_source=none; _gat_UA-72158538-1=1'
        }

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },

    }

    def filter_text(self,input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def start_requests(self):
        url = "https://www.smallable.com/en/"
        yield scrapy.Request(
            url=url,
            headers=self.headers
        )

    def parse(self, response):
        """主页"""
        url_list = ["https://www.smallable.com/en/fashion/baby/girl",
                    "https://www.smallable.com/en/fashion/baby/boy",
                    "https://www.smallable.com/en/shoes/baby",
                    "https://www.smallable.com/en/page/ski-baby",
                    "https://www.smallable.com/en/page/beach-baby",
                    "https://www.smallable.com/en/page/newborn-gifts",
                    "https://www.smallable.com/en/new/design/all/all/babycare",
                    "https://www.smallable.com/en/page/layette",
                    "https://www.smallable.com/en/design/all/all/pushchairs-baby-carrier-footmuffs",
                    "https://www.smallable.com/en/design/baby/all/beauty-and-care",
                    "https://www.smallable.com/en/fashion/children/girl",
                    "https://www.smallable.com/en/fashion/children/boy",
                    "https://www.smallable.com/en/shoes/children",
                    "https://www.smallable.com/en/page/ski-kids",
                    "https://www.smallable.com/en/page/beach-kids",
                    "https://www.smallable.com/en/fashion/children/all/accessories",
                    "https://www.smallable.com/en/design/children/all/beauty-and-care"
                    ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath('//a[@class="ProductCard_content__fBfLV"]/@href').getall()
        # detail_url_list = [response.urljoin(url) for url in detail_url_list]
        if detail_url_list:
            for detail_url in detail_url_list:
                # print(f"当前商品列表页有{len(detail_url_list)}条数据")
                detail_url = response.urljoin(detail_url)
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    headers=self.headers
                )

            next_page_url = response.xpath('//a[@class="SortMenu_pagination_item__1HRTk"]/@href').get()
            if next_page_url:
                next_page_url = response.urljoin(next_page_url)
                # print("下一页:"+next_page_url)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_list,
                    headers=self.headers
                )
        else:
            print(f"商品列表页无数据!:{response.url}")

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        name = response.xpath('//h2[@class="ProductDetails_name__2N5wD"]/text()').get()
        brand = response.xpath('//h1[@class="ProductDetails_brand__3ZBpv"]/a/text()').get()
        detail_cat_list = response.xpath('//span[@class="BreadCrumb_title__2o6Xv"]/text()').getall()
        cat = detail_cat_list[-1]
        detail_cat = str(detail_cat_list)
        description_list = response.xpath('//div[@class="ProductDetails_productDescription__5AV5h ProductDescription_container__3RG9h"]//text()').getall()
        description = " ".join(description_list)
        current_price = response.xpath('//span[@class="PriceLine_price__3rHav"]/text()').get()
        original_price = response.xpath('//span[@class="PriceLine_price__3rHav"]/text()').get()
        if current_price:
            items["current_price"] = current_price[1:]
            items["original_price"] = original_price[1:]
        else:
            items["current_price"] = original_price
            items["original_price"] = original_price
        items["brand"] = self.filter_text(brand)
        items["name"] = self.filter_text(name)
        items["detail_cat"] = detail_cat
        items["cat"] = cat
        images_list = list()
        images_info_list = response.xpath('//img[@class="ProductMediaSlider_img__2n6FN ProductMediaSlider_mobile__3UXay"]/@src').getall()
        for image in images_info_list:
            images_list.append("https:" + image)
        items["images"] = images_list
        items["url"] = response.url
        items["source"] = 'smallable.com'
        items["description"] = self.filter_text(description)

        items["sku_list"] = list()
        my_sku_list = []
        sku_id_list = response.xpath("//select[@id='form_size_select']").getall()
        if sku_id_list:
            for sku in sku_id_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                sku_html = etree.HTML(sku, parser=etree.HTMLParser(encoding="utf-8"))

                size_list_info = sku_html.xpath('//option[@class="oos"]/text()')
                size_list = list()
                for size_info in size_list_info:
                    size_list.append(size_info.replace(" ", "").replace("\n", "").split("-")[0])
                id_list = sku_html.xpath('//option[@class="oos"]/@value')

                if size_list and id_list:
                    for id in id_list:
                        for size in size_list:
                            sku_info = SkuItem()
                            sku_attr = SkuAttributesItem()
                            sku_info["sku"] = id
                            sku_attr["size"] = size
                            sku_info["attributes"] = sku_attr
                            sku_info["current_price"] = items["current_price"]
                            sku_info["original_price"] = items["original_price"]
                            my_sku_list.append(sku_info)

        if my_sku_list != []:
            items["sku_list"] = my_sku_list

        colors_list = response.xpath('//span[@class="ProductSiblingSelector_textSelected__30FPc"]/text()').getall()
        if colors_list:
            for other_product_url in colors_list:
                if not response.url in other_product_url:
                    # res = requests.get(other_product_url)
                    yield scrapy.Request(
                        url=other_product_url,
                        callback=self.parse_detail,
                        headers=self.headers
                    )

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
        # print(items)
        yield items
        # check_item(items)


