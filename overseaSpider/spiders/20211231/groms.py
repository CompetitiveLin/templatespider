# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux
from copy import deepcopy
from lxml import etree

website = 'groms'
scheme = 'https://www.groms.com/'


class EkobiecaSpider(scrapy.Spider):
    name = website
    allowed_domains = ['groms.com/']
    start_urls = ['https://www.groms.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(EkobiecaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "哲夫")

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT': 10,
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

    def parse(self, response):
        """获取全部分类"""
        # category_urls = response.xpath("//ul[@class='dropdown-menu']/li/a/@href").getall()
        category_urls = ['https://www.groms.com/products/tables','https://www.groms.com/products/storage','https://www.groms.com/products/storage',\
                         'https://www.groms.com/products/lighting','https://www.groms.com/products/decor','https://www.groms.com/products/seating',\
                         'https://www.groms.com/products/beds']
        for category_url in category_urls:
            if not category_url.startswith('http'):
                category_url = scheme + category_url
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='item product product-item']/div/a/@href").getall()
        for detail_url in detail_url_list:
            if not detail_url.startswith('http'):
                detail_url = scheme + detail_url
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail,
                dont_filter=True,
            )
        if '?p=' in response.url and int(response.url[-1]) < 9:
            next_page_url = response.url[:-1] + str( int(response.url[-1]) + 1 )
        elif '?p=' not in response.url:
            next_page_url = response.url + '?p=2'
        else:
            next_page_url = ''
        if next_page_url:
            if not next_page_url.startswith('http'):
                next_page_url = scheme + next_page_url
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_detail(self, response):
        item = ShopItem()
        item["source"] = 'groms.com'  # 来自哪个网站

        json_data = response.xpath("//script[@type='application/ld+json'][4]/text()").get()
        json_data = json.loads(json_data)

        item["name"] = json_data[0]['name']
        item["brand"] = json_data[0]['brand']

        cat_json_data = response.xpath("//script[@type='application/ld+json'][3]/text()").get()
        cat_json_data = json.loads(cat_json_data)
        detail_cat = [i['item']['name'] for i in cat_json_data['itemListElement']]
        item["cat"] = detail_cat[-1]
        item["detail_cat"] = '/'.join(detail_cat)

        item["measurements"] = ['Height: None', 'Length: None', 'Depth: None', 'Weight: None']
        description = re.findall(r'[<p>](.*?)[</p>]', json_data[0]['description'])
        item["description"] = ''.join(description)
        # item["description"] = response.xpath("//div[@class='whyWeLoveIt-message']/p/text()").get().replace("\n", "")
        item["url"] = response.url
        price = json_data[0]['offers']['price']
        item["original_price"] = '$' + str(price)  # 原价
        item["current_price"] = '$' + str(price)    # 现价

        # image_json_data = response.xpath("//script[@type='text/x-magento-init'][6]/text()").get()
        # image_json_data = json.loads(image_json_data)
        # images_list = [i['full'] for i in image_json_data["[data-gallery-role=gallery-placeholder]"]["mage/gallery/gallery"]['data']]  # 商品图片
        item["images"] = []

        item["sku_list"] = list()
        sku_json_data = response.xpath("//script[@type='text/x-magento-init'][1]/text()").get()
        sku_json_data = json.loads(sku_json_data)
        if list(sku_json_data.keys())[0] == '[data-role=swatch-options]':
            temp, = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonConfig']['attributes'].values()
            sku_id = temp['options']
            sku_id = [i['products'][0] for i in sku_id]
            sku_item_arr, = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonSwatchConfig'].values()
            if sku_id:
                for one_id in sku_id:
                    sku_item = SkuItem()
                    item_arr = SkuAttributesItem()
                    images_list = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonConfig']['images'][one_id]
                    images_list = [i['full'] for i in images_list]
                    sku_item["imgs"] = [response.urljoin(images) for images in images_list]
                    item["images"] += sku_item["imgs"]
                    original_price = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonConfig']['optionPrices'][one_id]['oldPrice']['amount']  # 原价
                    current_price = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonConfig']['optionPrices'][one_id]['finalPrice']['amount']
                    sku_item["original_price"] = '$' + str(original_price)    # 原价
                    sku_item["current_price"] = '$' + str(current_price)

                    item_arr_id, = sku_json_data["[data-role=swatch-options]"]["Magento_Swatches/js/swatch-renderer"]['jsonConfig']['index'][one_id].values()
                    item_arr['colour'] = sku_item_arr[item_arr_id]['label']
                    item_arr['colour_img'] = sku_item_arr[item_arr_id]['thumb']
                    sku_item["attributes"] = item_arr

                    item["sku_list"].append(sku_item)

        if item["images"] == []:
            image_json_data = response.xpath("//script[@type='text/x-magento-init'][6]/text()").get()
            image_json_data = json.loads(image_json_data)
            images_list = [i['full'] for i in image_json_data["[data-gallery-role=gallery-placeholder]"]["mage/gallery/gallery"]['data']]  # 商品图片
            item["images"] = [response.urljoin(images) for images in images_list]

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

        # detection_main(items=item,
        #                website=website,
        #                num=self.settings["CLOSESPIDER_ITEMCOUNT"],
        #                skulist=True,
        #                skulist_attributes=True)
        print(item)
        # yield item