# -*- coding: utf-8 -*-
import html
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.item_check import check_item

website = 'bunnings'

class BunningsSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['bunnings.com']
    # start_urls = ['http://bunnings.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(BunningsSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "凯棋")

    def delete_duplicate(self, oldlist):
        newlist = list(set(oldlist))
        newlist.sort(key=oldlist.index)
        return newlist

    def filter_html_label(self,text):
        if text:
            text = str(text)
            text = html.unescape(text)
            # 注释，js，css，html标签
            filter_rerule_list = [r'(<!--[\s\S]*?-->)', r'<script[\s\S]*?</script>', r'<style[\s\S]*?</style>', r'<[^>]+>']
            for filter_rerule in filter_rerule_list:
                html_labels = re.findall(filter_rerule, text)
                for h in html_labels:
                    text = text.replace(h, ' ')
            filter_char_list = [
                u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000', u'\u200a', u'\u2028', u'\u2029', u'\u202f', u'\u205f',
                u'\u3000', u'\xA0', u'\u180E', u'\u200A', u'\u202F', u'\u205F', '\t', '\n', '\r', '\f', '\v',
            ]
            for f_char in filter_char_list:
                text = text.replace(f_char, '')
            text = re.sub(' +', ' ', text).strip()
        return text


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
            "/products/tools",
            "/products/building-hardware",
            "/products/garden",
            "/products/outdoor-living",
            "/products/kitchen",
            "/products/bathroom-plumbing",
            "/products/curtains-blinds",
            "/products/paint-decorating",
            "/products/flooring-tiles",
            "/products/storage-cleaning",
            "/products/lighting-electrical",
            "/products/smart-home",
            "/products/hire-shop",
            "/products/indoor-living",
        ]
        for url in url_list:
            url = "https://www.bunnings.com.au" + url
            yield scrapy.Request(
                url=url,
            )

    def parse(self, response):
        url_list = response.xpath("//div[@class='CategoryListstyle__StyledGrid-sc-m7kjax-0 gdahCC']/div/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            url += "?page=1"
            print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """列表页"""
        # nums = response.xpath("//p[@class='MuiTypography-root showingResults MuiTypography-body1']/text()").get()
        # if nums:
        #     num = nums.split(" ")[-2]
        #     self.counts+=int(num)
        #     print(self.counts)
        a_list = response.xpath("//article/a")
        if a_list:
            for a in a_list:
                url = response.urljoin(a.xpath("./@href").get())
                price = a.xpath(".//p[contains(@data-locator, 'search-product-tile-price')]/text()").get()
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta={"price": price}
                )

            split_str = 'page='
            base_url = response.url.split(split_str)[0]
            page_num = int(response.url.split(split_str)[1])+1
            next_page_url = base_url + split_str + str(page_num)
            if next_page_url:
               next_page_url = response.urljoin(next_page_url)
               print("下一页:"+next_page_url)
               yield scrapy.Request(
                   url=next_page_url,
                   callback=self.parse_list,
               )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        price = response.meta.get('price', None)
        original_price = price
        current_price = price
        items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
        items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
        items["original_price"] = items["original_price"].replace('$','')
        items["current_price"] = items["current_price"].replace('$','')
        items["url"] = response.url
        json_str_list = response.xpath("//script[@type='application/ld+json']/text()").getall()
        for json_str in json_str_list:
            json_data = json.loads(json_str)
            if json_data["@type"] == "Product":
                break
        items["brand"] = json_data["brand"]["name"]
        items["name"] = json_data["name"]
        # attributes = list()
        # items["attributes"] = attributes
        # items["about"] = json_data["additionalProperty"]["value"]
        description = json_data["description"].replace("<br>", "")
        if description:
            items["description"] = self.filter_html_label(description)
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        items["source"] = website
        images_list = response.xpath("//div[@class='thumbnailImage']/img/@src").getall()

        if not images_list:
            image = json_data["image"]
            images_list.append(image)

        items["images"] = self.delete_duplicate(images_list)

        Breadcrumb_list = response.xpath("//nav[@aria-label='Breadcrumb']/ul/li/a/span/text()").getall()
        items["cat"] = Breadcrumb_list[-2]
        items["detail_cat"] = "/".join(Breadcrumb_list)

        sku_list = list()
        json_str = response.xpath("//script[@type='application/json']/text()").get()
        json_data1 = json.loads(json_str)
        baseOptions_list = json_data1["props"]["pageProps"]["initialState"]["productDetails"]["productdata"]["baseOptions"]
        for baseOptions in baseOptions_list:
            if "options" in baseOptions:
                options_list = baseOptions["options"]
                for option in options_list:
                    if option["productValues"]:
                        color = option["productValues"][0]["colorName"] if "colorName" in option["productValues"][0] else None
                        if color:
                            sku_item = SkuItem()
                            sku_item["original_price"] = items["original_price"]
                            sku_item["current_price"] = items["current_price"]
                            # sku_item["inventory"] = sku["inventory"]
                            # sku_item["sku"] = sku["sku"]
                            # imgs = list()
                            # sku_item["imgs"] = imgs
                            sku_item["url"] = response.url
                            # sku_item["sku"] = sku
                            attributes = SkuAttributesItem()
                            attributes["colour"] = color
                            # attributes["size"] = sku["size"]
                            # other = dict()
                            # attributes["other"] = other
                            sku_item["attributes"] = attributes
                            sku_list.append(sku_item)

        items["sku_list"] = sku_list
        status_list = list()
        status_list.append(items["url"])
        status_list.append(items["original_price"])
        status_list.append(items["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        items["id"] = md5(status.encode("utf8")).hexdigest()
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
        items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        items["created"] = int(time.time())
        items["updated"] = int(time.time())
        items['is_deleted'] = 0
        print(items)
        # check_item(items)
        # yield items