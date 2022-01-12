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

website = 'chickapig'
headers = {
    'authority': 'chickapig.shop.musictoday.com',
    'cache-control': 'max-age=0',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-dest': 'document',
    'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
    'cookie': 'JSESSIONID=owEUfvs1HAYQ77Z6JmETkSWo.sms-cms11p; MTEmailPopup="shown=true"; MTSession="SessionID=8fb64506-eb4c-4104-8025-413e5c32943e&Domain=chickapig.shop.musictoday.com"; MTCurrency="Currency=USD&Domain=chickapig.shop.musictoday.com"; _gcl_au=1.1.986048880.1638779453; _ga=GA1.2.1828294306.1638779455; _gid=GA1.2.1477260747.1638779455; __cf_bm=SX0JYeBo09KSmABtiehaoSUKkZ2_W8LsJbf1Fne1GIE-1638781250-0-AZW9yEU4zN7u7UP7XMQhr+IcpBXhK+ej34InjZvj9pQOQIsW0Rk86sR51Tx8wRqEooFEl02PnjRGWB39OXvI/J/gWHht9dnW86YT/jaZL4vt; JSESSIONID=owEUfvs1HAYQ77Z6JmETkSWo.sms-cms09p; _dc_gtm_UA-52609340-1=1; _dc_gtm_UA-6452073-68=1',
}

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
    allowed_domains = ['chickapig.shop.musictoday.com']
    start_urls = ['https://www.chickapig.com/']

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
        'DOWNLOAD_HANDLERS': {
            "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
        }
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
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', ', ', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):

        category_urls = ['https://chickapig.shop.musictoday.com/dept/books?cp=104835_107182',
                         'https://chickapig.shop.musictoday.com/dept/games?cp=104835_107181',
                         'https://chickapig.shop.musictoday.com/dept/shirts?cp=104835_104960_104961',
                         'https://chickapig.shop.musictoday.com/dept/hats?cp=104835_104960_104964']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list, headers=headers,meta={'h2':True})

    def parse_list(self, response):
        """商品列表页"""
        print(111111111)
        detail_url_list = response.xpath("//ul[@id='ProductGridComponent_ProductGrid_2_productGrid']/li/div/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail,headers=headers,meta={'h2':True})
    def parse_detail(self, response):
        print(22222222)
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='Pricing']/ul/li[@class='RegularPricing']/span[@class='PriceValue']").get()
        if not price:
            return
        price = self.filter_text(price)
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//div[@id='ProductNameComponent_ProductName_1']/div/text()").get()
        name = name.replace('\n','')
        name = name.strip()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='Breadcrumbs hidden-xs hidden-sm']/li/a/text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@id='collapse1_ProductDescriptionComponent_ProductDetails_1']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//div[@class='AltViews hidden-xs hidden-sm MainThumbnails AltViewsBelow']/ul/li//img/@src").getall()
        items["images"] = images_list
        items["brand"] = ''

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
        item_check.check_item(items)
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        print(items)
        yield items
