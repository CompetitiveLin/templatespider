# -*- coding: utf-8 -*-
import re
import json
import time

import demjson
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main

website = 'paulayoung'

class PaulayoungSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['https://www.paulayoung.com/']
    # start_urls = ['http://https://www.paulayoung.com//']
    headers = {
        'authority': 'www.paulayoung.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'referer': 'https://www.paulayoung.com/category/wigs/all-wigs.do?c=4.106174&sortby=bestSellersAscend&pp=60',
        'accept-language': 'zh-CN,zh;q=0.9',
        # 'cookie': f"_vuid=e5070ab4-6cc4-437d-847b-1c86f4cdf2df; _vuid=e5070ab4-6cc4-437d-847b-1c86f4cdf2df; JSESSIONID=EF4E951989B63675990E5DAB971CE77E.b2c-paulayoung-prdv162-app004; customer=none; basket=none; _evga_9c05=4e0a4557ffb3dd35.; _sp_ses.16e7=*; ak_bmsc=965BC98BC39F65A509AC654B481C1351~000000000000000000000000000000~YAAQlOI+FwfsK9d7AQAAtVvG3A0vTQI5aMFYGB08KiIZoRvJ8LRzY+zahPdoo78YDzSnWSFeFQVQoncLBp8nyqoSsSPcXNm1h6Tbd9n//hzZMeMlEcrpiWPTI8uzd8X1PGpUpoYuMU44YqIqRmrpdiAgenFH+X2aMdWmnRcBmyQnTHsH48TnSr0ceAfPoMbX+KzuTvYZB1CRyQ71Lgz3d1KXySQtO82cOzqTk1fZPQ1hH+PVQ0nEUCgoXXCHS5JXdAp+LAnxBt1adG0PN8lXAxwStcQuSW70D1H/OjAqk1yrAPErvJFQsJJFubhgO+xnJoVSkiq67n0gLwlSOd8rQnggD3Akm6WK+lOInbkN6cZEHiPow1rr7fL5qujinU+hPUaQnqKAQFz30koVctfnntSF0uiYnqrGBMONmSklNsWd1BoxT7MOP2vex6lPrADxlNL5tEPIWky3t2kcmq40KrGZOxMP31JFI0c5jOFF37pMM168Mr9iNnNX9mIu8WAf; ltkSubscriber-Footer=eyJsdGtDaGFubmVsIjoiZW1haWwiLCJsdGtUcmlnZ2VyIjoibG9hZCIsImx0a0VtYWlsIjoiIn0%3D; ltkpopup-suppression-9f802612-9b86-456e-a148-12f6caff624f=1; STSID371958=5ae198be-d686-4ae0-ac37-a8a57813d005; GSIDXH9Jg8f3dSyC=1492d214-04e1-4956-8831-2134ebd84878; _ga=GA1.2.566920808.1631496590; _gid=GA1.2.715920501.1631496590; _vuid=e5070ab4-6cc4-437d-847b-1c86f4cdf2df; _fbp=fb.1.1631496590668.1916308451; _svsid=8fb233fee46565c7f818bc18c356a23f; s_fid=2830EF6B1E18A9CF-179111A0D28C8CE4; pv_touchNoticeFlag=N; __atuvc=4%7C37; __atuvs=613ea9dcfadc1c05003; _gat=1; bm_sv=81B7029AF6660B8A7651EA7EA2BFA2B0~16e8Ep0J7x8kvSu7ic7QzJ85mT/xpwUuaOMjxNmAA+IpIWQ8i3cSJMopvISPnzFoqF2Y6Ll98QDI0UK/ckjMyV5pJfcVsBWkH0MNKgeYLRLEuSO84YN+cBgihcqCJ6cU2e2FZ77KUIRNgHRxh9vb8Zqty297IE467oT6aNuKPEI=; utag_main=v_id:017bdcc6514000019a9b38a047c903072001b06a007e8{_sn:1$_ss:0$_pn:30%3Bexp-session$_st:1631499131484$ses_id:1631496589632%3Bexp-session$_prevpage:All%20Wigs%3Bexp-1631500931499;} ltkpopup-session-depth=23-24; _sp_id.16e7=6bd8a3ab2d627465.1631496588.1.1631497334.1631496588; cto_bundle=nORLsV9JJTJCT2t6ZFA3UDJxY2VuSW1ZUHlaciUyQlZNM0VuMFJvdnVobWhoaDhYV2tWdkxsUTl1bnVnRTFOTnNWaDcxZTZxRHQ1enltbExtckhsc0ZPNWtHcjhkaUx0U3dMMmJMTWFNeVZVVVRLcFFtWWpkTjhrcTFYR2wyTk02VDBEZDc4ZnNXeXF4aWVPZHE3VWZhT2dwcmttV253JTNEJTNE",
    }

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings['CLOSESPIDER_ITEMCOUNT'] = 20
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(PaulayoungSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "肥鹅")

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
            'https://www.paulayoung.com/category/wigs/all-wigs.do?c=4.106174&sortby=bestSellersAscend&pp=60&page=1',
            'https://www.paulayoung.com/category/wiglets/all-wiglets.do?c=331813.331843&sortby=bestSellersAscend&pp=60&page=1',
            'https://www.paulayoung.com/category/hairpieces/all-hair-pieces.do?c=5.331730&sortby=bestSellersAscend&pp=60&page=1',
            'https://www.paulayoung.com/category/clearance/all-clearance.do?c=101607.332166&sortby=bestSellersAscend&pp=60&page=1'
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                headers=self.headers
            )

        #url = "http://https://www.paulayoung.com//"
        #yield scrapy.Request(
        #    url=url,
        #)

    def parse(self, response):
        url_list = response.xpath("//div[@id='ml-grid-view-items']/div/div/div/div/div/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            # url = 'https://www.paulayoung.com/product/flynn-whisperlite-wig-by-paula-young.do?sortby=ourPicks&from=fn'
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                headers=self.headers
            )

        if url_list:
            next = response.url.split('&page=')[0] + '&page=' + str(int(response.url.split('&page=')[1])+1)
            # print('下一页 '+next)
            yield scrapy.Request(
                url=next,
                callback=self.parse,
                headers=self.headers
            )


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["name"] = response.xpath("//div[@class='ml-product-name']/div/text()").get()
        original_price = response.xpath("//div[@id='ml-price-ticket']/div[@class='ml-price-value']/text()").get().replace(',','')
        # attributes = list()
        # items["attributes"] = attributes
        # items["about"] = response.xpath("").get()
        items["description"] = response.xpath("//div[@id='accordionTarget01']/div[@class='panel-body']/text()").get() + ' ' + response.xpath("//div[@class='ml-product-desc-short']/text()").get()
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        items["source"] = website
        images_list = response.xpath("//div[@id='detailViewContainer']/div/a/img/@src").getall()
        if not images_list:
            images_list = response.xpath("//div[@class='ml-product-alt-detailimgcontainer']/div/a/img/@src").getall()
        for i in range(len(images_list)):
            images_list[i] =  images_list[i].split('&')[0]+'&'+images_list[i].split('&')[-1]
        items["images"] = images_list
        detail_cat = ''
        Breadcrumb_list = response.xpath("//ol[@class='breadcrumb']/li/a/text()").getall()
        items["cat"] = response.xpath("//ol[@class='breadcrumb']/li[@class]/text()").get()
        for b in Breadcrumb_list:
            b = b.replace('\r','').replace('\n','').replace('\t','').strip(' ')
            if b:
                detail_cat = detail_cat + b + '/'
        items["detail_cat"] = detail_cat + items["cat"]

        sku_list = list()
        color_index = {}
        color_imgs = response.xpath("//div[@id='ViewLargerCarouselWrapper']/div/img")
        for c in color_imgs:
            color_index[c.xpath("./@alt").get()]='https://www.paulayoung.com'+c.xpath("./@src").get()
        sku_content = response.xpath("//script[@type='text/javascript']/text()").getall()
        for s in sku_content:
            if 'utag_data' in s:
                sku_content = s
                break
        sku_content = sku_content.replace('customer_type','"customer_type"').replace('site_type','"site_type"').replace('page_type','"page_type"').replace('cart_total_items','"cart_total_items"').replace('product_option_value','"product_option_value"').replace('logged_in','"logged_in"').replace('product_option_type','"product_option_type"').replace('product_price','"product_price"').replace('product_name','"product_name"').replace('external_user_id','"external_user_id"').replace('product_sku','"product_sku"').replace('account_id','"account_id"').replace('active_site','"active_site"').replace('cart_order_subtotal','"cart_order_subtotal"').replace('page_name','"page_name"').replace('product_id','"product_id"').replace('expiration','"expiration"').replace('product_brand','"product_brand"').replace('product_category','"product_category"').replace("var utag_data=",'').replace(';','')
        sku_content = demjson.decode(sku_content)
        for sku,price in zip(sku_content['product_option_value'],sku_content['product_price']):
            sku_item = SkuItem()
            sku_item["original_price"] = self.price_fliter(original_price)
            sku_item["current_price"] = str(price).replace(',','')
            attributes = SkuAttributesItem()
            attributes["colour"] = sku[1][0]
            for ind in color_index.keys():
                if ind == attributes["colour"]:
                    attributes["colour_img"] = color_index[ind]
            attributes["size"] = sku[1][1]
            sku_item["attributes"] = attributes
            sku_list.append(sku_item)

        items["sku_list"] = sku_list
        items["brand"] = sku_content['product_brand'][0]
        current_price = sku_list[0]['current_price']
        items["original_price"] = self.price_fliter("" + str(original_price) if original_price else "" + str(current_price))
        items["current_price"] = self.price_fliter("" + str(current_price) if current_price else "" + str(original_price))
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
        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                skulist_attributes=True)
        yield items


    def price_fliter(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ', '$', '€', ',', '\n',
                       '¥']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text