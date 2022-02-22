# -*- coding: utf-8 -*-
import re
import time
import json
import scrapy
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux
from overseaSpider.util.item_check import check_item
from lxml import etree
from overseaSpider.items import ShopItem, SkuItem, SkuAttributesItem
from overseaSpider.util.scriptdetection import detection_main

website = 'campingworld'

class CampingworldSpider(scrapy.Spider):
    name = website
    # start_urls = ['https://www.campingworld.com/']


    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUN"] = 30
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(CampingworldSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "泽塔")

        self.headers = {
            'authority': 'www.campingworld.com',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': 'dwac_12144fa399195acdf36cc8e1eb=tjSwK-VTlXrXumVpzRoi1Yk1l0PRJ-fv2tM%3D|dw-only|||USD|false|US%2FCentral|true; cqcid=abQK6JunyTggpSmAAz4T7O9lFv; cquid=||; sid=tjSwK-VTlXrXumVpzRoi1Yk1l0PRJ-fv2tM; dwanonymous_4766eb4552e1e03c5cc9b10183ad4284=abQK6JunyTggpSmAAz4T7O9lFv; __cq_dnt=0; dw_dnt=0; dwsid=3AwusJtLuWU2y43C7THLdOMNCdivP8vwO6JGujsqYAFt-pwPxB7Dqyg-05h1bzTxVByOU7L1QqqWkMB4giVAuA==; _gcl_au=1.1.1214920282.1630030180; dw=1; dw_cookies_accepted=1; _caid=48a362e5-3cac-469a-9c96-0286381072f0; _cavisit=17b855eb337|; _ga=GA1.2.2107286707.1630030181; _gid=GA1.2.869826103.1630030181; ajs_anonymous_id=%226fe0cd71-371b-4a56-8938-a88ade949e58%22; _hjid=a9a42278-3586-47c7-acfe-2f050de7e18d; _hjFirstSeen=1; _hjIncludedInSessionSample=0; _hjAbsoluteSessionInProgress=0; __idcontext=eyJjb29raWVJRCI6IlkyQ0ZUT0VXWlE3UDNJVTNSWkEyREhMNzVCVkpIQUZZVk4zTExYT1JNNkJRPT09PSIsImRldmljZUlEIjoiWTJDRlRPRVdaUlk0SkhOT1NVWTJYRFlYWEpFNzVKVkVaSU5aWkpVQ05DSEE9PT09IiwiaXYiOiI3WUhENU8zWDU2QVRFVzVIUlYyVVhTTUcyST09PT09PSIsInYiOjF9; bounceClientVisit2810v=N4IgNgDiBcIBYBcEQM4FIDMBBNAmAYnvgO6kB0AxgIYC2EAlgHYDmxA9gE5gAmlbNREABoQHGCGEgUAU2YwA2gF0AvkA; __cq_uuid=bdDrsay2D81HjWYZaLPH4dbv4C; __cq_seg=0~0.00u00211~0.00u00212~0.00u00213~0.00u00214~0.00u00215~0.00u00216~0.00u00217~0.00u00218~0.00u00219~0.00; IR_gbd=campingworld.com; BVBRANDID=cbcd6d62-d805-445b-b4e5-6d39bdffbfe1; BVBRANDSID=9a2eb978-20bc-4826-948d-f9116040e632; _scid=4ee13265-b830-4506-a9c5-8b9cd1ce812f; _fbp=fb.1.1630030191379.1398501392; _sctr=1|1629993600000; cnx_sid=376694956032065973; cnx_start=1630030193783; cnx_rid=1630030193192996212; LPVID=M5ZmNkN2FhYTk5NjcwNzRk; LPSID-41948688=dHrDGXXLTMetwcLozeknOA; _dc_gtm_UA-6012758-7=1; IR_10998=1630030337482%7C0%7C1630030185433%7C%7C; _uetsid=d94f849006db11ecbee0c39921a0d0ad; _uetvid=d94ff85006db11ecb92f5912fea6ab49; stc117009=tsa:1630030191658.506947090.1412387.5876323954740208.1:20210827024217|env:1%7C20210927020951%7C20210827024217%7C3%7C1065174:20220827021217|uid:1630030191658.1060401904.6376996.117009.478448827.:20220827021217|srchist:1065174%3A1%3A20210927020951:20220827021217; cnx_views=3; cnx_pg=1630030338849; cnx_t_views=3; __cq_dnt=0; dw_dnt=0'
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

    def filter_html_label(self, text, type):
        html_labels_zhushi = re.findall('(<!--[\s\S]*?-->)', text)  # 注释
        if html_labels_zhushi:
            for zhushi in html_labels_zhushi:
                text = text.replace(zhushi, '')
        html_labels = re.findall(r'<[^>]+>', text)  # html标签
        if type == 1:
            for h in html_labels:
                text = text.replace(h, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

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
        url = "https://www.campingworld.com/"
        yield scrapy.Request(
            url=url,
            headers=self.headers
        )

    def parse(self, response):
        """主页"""
        url_list = ['https://www.campingworld.com/inside-rv','https://www.campingworld.com/outside-rv','https://www.campingworld.com/maintain-rv',\
                    'https://www.campingworld.com/covers','https://www.campingworld.com/rv-stabilization-auto','https://www.campingworld.com/generators',\
                    'https://www.campingworld.com/camping','https://www.campingworld.com/hitch-tow','https://www.campingworld.com/electronics',\
                    'https://www.campingworld.com/active-sport','https://www.campingworld.com/boating-watersports','https://www.campingworld.com/apparel-footwear','https://www.campingworld.com/fishing',\
                    'https://www.campingworld.com/lifestyle','https://www.campingworld.com/shop-select-towable-rvs']
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_1,
                headers=self.headers
            )

    def parse_1(self, response):
        catagory_list = response.xpath('//a[@class="category-tile text-placement-below aspect-ratio-square  "]/@href').getall()
        if catagory_list:
            catagory_list = [response.urljoin(url) for url in catagory_list]
            for url in catagory_list:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_list,
                    headers=self.headers
                )
        else:
            detail = response.xpath('//a[@class="link"]/@href').getall()
            detail = [response.urljoin(url) for url in detail]
            for url in detail:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    headers=self.headers
                )





    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath('//a[@class="link"]/@href').getall()
        detail_url_list = [response.urljoin(url) for url in detail_url_list]
        for detail_url in detail_url_list:
            # print("详情页url:"+detail_url)
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail,
                headers=self.headers
            )


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        # [CATEGORY]
        detail_cat_list = response.xpath("//ol[@class='breadcrumb']/li/a/text()").getall()
        detail_cat_list = [detail.replace("\n", "").replace(" ", "") for detail in detail_cat_list]
        detail_cat = str(detail_cat_list).replace("[", "").replace("]", "").replace("'", "").replace('"', '').replace(", ", "/")
        cat = detail_cat.split("/")[-1]
        # [NORMAL PRICE]
        judge_string = "True"
        current_price = response.xpath('//span[@class="price-label sale-price"]/text()').get()[1:]
        items["current_price"] = current_price.strip().replace(",", "")
        original_price = response.xpath('//span[@class="price-label sale-price"]/text()').get()[1:]
        items["original_price"] = original_price.strip().replace(",", "")
        judge_string = 'True'
        if judge_string == "True":
            html_json_data = re.findall('products":(\[.*\])', response.text)
            html_json_data = html_json_data[0]
            json_data_info = '{"INFO":' + str(html_json_data) + '}'
            json_data_info = json.loads(json_data_info)
            json_data = json_data_info["INFO"][0]
            # [OTHER ITEMS]
            if "brand" in json_data:
                items["brand"] = json_data["brand"]
            else:
                items["brand"] = "Campingworld"
            items["name"] = json_data["name"].replace("&quot;", '"')
            items["detail_cat"] = detail_cat
            items["cat"] = cat
            # [IMAGES INFO]
            images_list = response.xpath("//a[@class='thumbnail-link']/@href").getall()
            if images_list:
                items["images"] = images_list
            else:
                images_list = response.xpath("//meta[@property='og:image']/@content").get()
                items["images"] = [images_list]
            items["url"] = response.url
            items["source"] = website
            description = response.xpath("//div[@class='visible-content active']").get()
            description = self.filter_html_label(str(description), 1)
            items["description"] = self.filter_text(description)
            items["sku_list"] = list()
            # [SKU INFO]
            my_sku_list = list()
            sku_color_list = response.xpath("//ul[@class='swatches color']//a[@class='swatchanchor']/img/@alt").getall()
            sku_size_list = response.xpath("//ul[@class='swatches width']//a[@class='swatchanchor']/text()").getall()
            sku_size_list = [size.replace("&quot;", '"') for size in sku_size_list]
            if sku_color_list and sku_size_list:
                for color in sku_color_list:
                    for size in sku_size_list:
                        sku_info = SkuItem()
                        sku_attr = SkuAttributesItem()

                        sku_attr["colour"] = color
                        sku_attr["size"] = size
                        sku_info["current_price"] = items["current_price"]
                        sku_info["original_price"] = items["original_price"]
                        sku_info["attributes"] = sku_attr
                        my_sku_list.append(sku_info)
            else:
                if sku_size_list:
                    for size in sku_size_list:
                        sku_info = SkuItem()
                        sku_attr = SkuAttributesItem()

                        sku_attr["size"] = size
                        sku_info["current_price"] = items["current_price"]
                        sku_info["original_price"] = items["original_price"]
                        sku_info["attributes"] = sku_attr
                        my_sku_list.append(sku_info)
                elif sku_color_list:
                    for color in sku_color_list:
                        sku_info = SkuItem()
                        sku_attr = SkuAttributesItem()

                        sku_attr["colour"] = color
                        sku_info["current_price"] = items["current_price"]
                        sku_info["original_price"] = items["original_price"]
                        sku_info["attributes"] = sku_attr
                        my_sku_list.append(sku_info)

            if my_sku_list != []:
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

            # detection_main(
            #     items=items,
            #     website=website,
            #     num=self.settings["CLOSESPIDER_ITEMCOUNT"],
            #     skulist=True,
            #     skulist_attributes=True
            # )
            print(items)
            # yield items
            # check_item(items)


