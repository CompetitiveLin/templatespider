# -*- coding: utf-8 -*-
import html
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'hoanhtao'


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
    allowed_domains = ['hoanhtao.com']
    start_urls = ['https://www.hoanhtao.com/']

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

    def filter_html_label(self, text):
        text = str(text)
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
        text = html.unescape(text)
        text = re.sub(' +', ' ', text).strip()
        return text

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = ['https://www.hoanhtao.com/l-o-l-surprise-sale/',
                         'https://www.hoanhtao.com/melissa-and-doug-sale/',
                         'https://www.hoanhtao.com/leapfrog-new-toys/',
                         'https://www.hoanhtao.com/disney-toys-collection-sale/',
                         'https://www.hoanhtao.com/funko-toys-sale-on-us/',
                         'https://www.hoanhtao.com/barbie-the-toys-on-sale/',
                         'https://www.hoanhtao.com/thomas-friends-toys-clearance-sale/',
                         'https://www.hoanhtao.com/lego-toys-deals/']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list, meta={"page":1})

    def parse_list(self, response):
        """商品列表页"""
        page = response.meta.get("page")
        detail_url_list = response.xpath("//div[@class='product-thumb']/a[@class='product-url']/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        number_str = response.xpath("//h5/span/text()").get()
        number = number_str.replace("(",'')
        number = number.replace(")",'')
        number = int(number)
        if page*48 < number:
            page = page+1
            url = response.url
            if url.find("?p=")!=-1:
                index = url.find("?p=")
                url = url[:index]
            next_page_url = url+"?p="+str(page)
            yield scrapy.Request(url=next_page_url, callback=self.parse_list, meta={"page":page})

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_old = response.xpath("//div[@class='product-title-price']//span[@class='old-price']/span/text()").get()
        price_new = response.xpath("//div[@class='product-title-price']//span[@class='special-price']/span/text()").get()
        price_new = price_new.replace("\n",'')
        price_new = price_new.replace(" ",'')
        price_new = price_new.replace("$",'')
        price_new = self.filter_text(price_new)
        if price_old:
            price_old = price_old.replace("\n", '')
            price_old = price_old.replace(" ", '')
            price_old = price_old.replace("$", '')
            price_old = self.filter_text(price_old)
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumb hidden-xs']/li/a/text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='details-heading-text']/div[@class='details-content']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//div[@class='product-medis-thumbs visible-md visible-lg']/ul[@class='list-unstyled']/li//img/@src").getall()
        for i in range(len(images_list)):
            images_list[i]=images_list[i].replace("80x","1000x")
        items["images"] = images_list
        items["brand"] = ''
        attr_list_tmp = response.xpath("//div[@class='details-content']/div").getall()
        if attr_list_tmp:
            attr_list = []
            for a in attr_list_tmp:
                a = self.filter_text(self.filter_html_label(''.join(a)))
                attr_list.append(a)
                items["attributes"] = attr_list

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
        # item_check.check_item(items)
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
