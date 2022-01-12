# -*- coding: utf-8 -*-
import math
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'portobello-decoration'


def get_sku_price(product_id, attribute_list):
    """获取sku价格"""
    url = 'https://thecrossdesign.com/remote/v1/product-attributes/{}'.format(product_id)
    data = {
        'action': 'add',
        'product_id': product_id,
        'qty[]': '1',
    }
    for attribute in attribute_list:
        data['attribute[{}]'.format(attribute[0])] = attribute[1]
    response = requests.post(url=url, data=data)
    return json.loads(response.text)['data']['price']['without_tax']['formatted']


class ThecrossdesignSpider(scrapy.Spider):
    name = website
    allowed_domains = ['portobello-decoration.fr']
    start_urls = ['https://portobello-decoration.fr/']

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
        super(ThecrossdesignSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "叶复")

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
    }

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'<div class="cbb-frequently-bought-container cbb-desktop-view".*?</div>', r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
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
        category_urls = response.xpath("//ul[@class='sub-sub-menu color-scheme-dark']/li[contains(@class,'menu-item menu-item-type-taxonomy menu-item-object-product_cat') and @id]/a/@href").getall()
        # print(category_urls)
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list, meta={'url':category_url})

    def prase_list_temp(self,response):
        detail_url_list = response.xpath("//div[@class='product-element-top']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)

    def parse_list(self, response):
        """商品列表页"""
        # detail_url_list = response.xpath("//div[@class='product-element-top']/a/@href").getall()
        # for detail_url in detail_url_list:
        #     yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        base_url=response.meta.get('url')
        str_page = response.xpath("//p[@class='woocommerce-result-count']/text()").get()
        str_page = str_page.strip()
        if len(str_page)>30:
            index_start=str_page.find('sur')
            index_end=str_page.find('résultats')
            page_number = math.ceil(int(str_page[index_start + 4:index_end].strip()) / 24)
            for i in range(page_number):
                next_page_url = base_url+'page/'+str(i+1)
                yield scrapy.Request(url=next_page_url, callback=self.prase_list_temp)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//p[@class='price']/span/bdi/text()").get()
        price = price.replace(',','')
        price = price.replace(' ','')
        # price = price if '-' not in price else price.split('-')[0]
        items["original_price"] = price
        items["current_price"] = items["original_price"]

        name = response.xpath("//h1[@class='product_title entry-title']/text()").get()
        items["name"] = name

        cat_list = response.xpath("//nav[@class='woocommerce-breadcrumb']/a/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)
        print(cat_list)
        description = response.xpath("//div[@class='woocommerce-product-details__short-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath('//ul[@class="productView-thumbnails"]/li/a/@href').getall()
        items["images"] = images_list

        size_list = []
        attr_id = 0
        label_list = response.xpath('//form[@class="form"]/div[1]/div[@class="form-field"]')
        for label in label_list:
            key = label.xpath('./label[1]/text()').get().strip().replace(':', '').lower()
            values = label.xpath('./label')[1:]
            if 'size' in key:
                attr_id = values[0].xpath('./following-sibling::input[1]/@name').get()
                size_list = [{'id': v.xpath('./@data-product-attribute-value').get(), 'value': v.xpath('./span[1]/text()').get().strip()} for v in values]

        product_id = re.search(r'"product_id":"(.*?)",', response.text).group(1)
        sku_list = list()
        for size in size_list:
            sku_info = SkuItem()
            sku_attr = SkuAttributesItem()
            sku_attr["size"] = size['value']
            price = get_sku_price(product_id, [(attr_id, size['id'])])
            sku_info["current_price"] = price
            sku_info["original_price"] = price
            sku_info["attributes"] = sku_attr
            sku_list.append(sku_info)
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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        print(items)
        yield items
