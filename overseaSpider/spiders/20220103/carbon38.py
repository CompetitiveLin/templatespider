# -*- coding: utf-8 -*-
import re
import json
import time

import demjson
import scrapy
import requests
from hashlib import md5

from lxml import etree

from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'carbon38'


class Carbon38Spider(scrapy.Spider):
    name = website

    # allowed_domains = ['carbon38.com']
    # start_urls = ['http://carbon38.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(Carbon38Spider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "云棉")
        self.headers = {
            'authority': 'www.carbon38.com',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh,zh-CN;q=0.9,en;q=0.8',
            'cookie': 'pxcts=0953d941-0a0f-11ec-b943-0d7f31063467; _pxvid=0953b7e3-0a0f-11ec-830a-704a79616e75; form_key=us44sSIYbLJb5IdF; webp=1; mage-cache-storage=%7B%7D; mage-cache-storage-section-invalidation=%7B%7D; PHPSESSID=213aca251e592242a0dbe79a1db2656d; visitor_id=41596473; visitor_country_code=N%2FA; c38_utm_source=20.81.114.208%3A8000; c38_utm_medium=referral; visits_counter_flag=1630382032; X-Magento-Vary=1a6e6799729a7e9386d54086f3dce42eda247d27; recently_viewed_product=%7B%7D; recently_viewed_product_previous=%7B%7D; recently_compared_product=%7B%7D; recently_compared_product_previous=%7B%7D; product_data_storage=%7B%7D; _gcl_au=1.1.753609283.1630382035; _ga=GA1.2.1765901909.1630382035; _gid=GA1.2.889249147.1630382035; _fbp=fb.1.1630382036730.419218511; RES_TRACKINGID=450614863936508; RES_SESSIONID=847074839493207; ResonanceSegment=1; __attentive_id=dca987e02481432493e1e22490c91112; __attentive_cco=1630382039056; __attentive_ss_referrer="http://20.81.114.208:8000/"; __attentive_dv=1; mage-cache-sessid=true; s38=undefined%3Aundefined; __kla_id=eyIkcmVmZXJyZXIiOnsidHMiOjE2MzAzODIwMjMsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly93d3cuY2FyYm9uMzguY29tLyJ9LCIkbGFzdF9yZWZlcnJlciI6eyJ0cyI6MTYzMDM4MzM1MiwidmFsdWUiOiJodHRwOi8vMjAuODEuMTE0LjIwODo4MDAwLyIsImZpcnN0X3BhZ2UiOiJodHRwczovL3d3dy5jYXJib24zOC5jb20vIn19; _pxff_tm=1; g38=undefined; p38=50; pageViewed=20; _px3=39ed71d42b3971fb4150af772308beebae66f7276ba5c3166b6b44d896476153:4f4yEVIr73oMAL1m5P4l+x1VdK/19V0h+vyL4zXhCjU8NlbRiBy12vniecNgw/6jNHEEOmzyXlPHmC4MqIWVlg==:1000:Nec55hORBoGXARBzwnBfNwyDkw0of+VEK7PrdTyofecxRiPG233a/FS5pcHYeAyr9Py8PNcxVqtI7iASD8wBT5uoSIrATWDvEP+HGnBNMnZYCcu6GDuvtORBLYQ7az+gFx/qXUzRVCxKGuj1ohPvlAwhYIF+9sZk1WHys7W8Ub3wIYKnMxEr0Kpp20VKoqkOimYTxm0pER0rsXK9Uv6Hkg==; private_content_version=6309175a702fa093607bd6474620b909; section_data_ids=%7B%22messages%22%3A1630383355%2C%22newsletter%22%3A1630383355%2C%22datalayer-user%22%3A1630382086%2C%22datalayer-basket%22%3A1630382086%7D; _gat_UA-36740325-1=1; _uetsid=101369800a0f11ec9cfcab595ad34114; _uetvid=10137a000a0f11ec99274740a499849d; __idcontext=eyJjb29raWVJRCI6IkxWRVFBUU9PRENaRDVCRURKRTJHNDNBNFZMRDJGTUZSQTY2TTZOWFYyMzRBPT09PSIsImRldmljZUlEIjoiTFZGWDJZTzRER1RITFlIN01ZNFdHVVlKNjNWSlZMRjdHR1M1NkVGRDY3NFE9PT09IiwiaXYiOiJPUFI0SlVONUw0NEtESkVQUkw0VlZTRzZMND09PT09PSIsInYiOjF9; __attentive_pv=20'
        }

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT': 10,
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
        # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        url_list = [
            'https://carbon38.com/what-s-new/new-arrivals',
            'https://carbon38.com/collections/all-exclusives',
            'https://carbon38.com/what-s-new/best-sellers',
            'https://carbon38.com/collections/shop-all',
            'https://carbon38.com/collections/shoes',
            'https://carbon38.com/collections/accessories',
            'https://carbon38.com/sale'
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                headers=self.headers
            )

    def parse(self, response):
        url_list = response.xpath('//div[@class="product-info"]//a[@class="product-link"]/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_detail,
            )
        next_page_url = response.xpath('//link[@rel="next"]/@href').get()

        if next_page_url:
            # print("下一页:"+next_page_url)
            next_page_url = response.urljoin(next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                headers=self.headers
            )

    def filter_html_label(self, text):
        html_labels_zhushi = re.findall('(<!--[\s\S]*?-->)', text)  # 注释
        if html_labels_zhushi:
            for zhushi in html_labels_zhushi:
                text = text.replace(zhushi, '')
        html_labels = re.findall(r'<[^>]+>', text)  # html标签
        for h in html_labels:
            text = text.replace(h, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('\xa0', '').replace('  ', '').replace(
            'US', '').strip()
        return text

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        price = self.price_fliter(response.xpath('//span[@class="current-price theme-money"]/text()').get())
        items["original_price"] = price
        items["current_price"] = price
        # price_info = response.xpath('//script[@type="text/x-magento-init"]//text()').getall()
        # size_info = ''
        # for price in price_info:
        #     if '[data-role=swatch-options]' in price:
        #         price = demjson.decode(price)
        #         original_price_info = price.get("[data-role=swatch-options]").get(
        #             "Magento_Swatches/js/swatch-renderer").get("jsonConfig").get("prices").get('oldPrice').get('amount')
        #         current_price_info = price.get("[data-role=swatch-options]").get(
        #             "Magento_Swatches/js/swatch-renderer").get("jsonConfig").get("prices").get('finalPrice').get(
        #             'amount')
        #         if original_price_info:
        #             original_price = original_price_info
        #             current_price = current_price_info
        #             items["original_price"] = "$" + str(original_price)
        #             items["current_price"] = "$" + str(current_price)
        #         else:
        #             current_price = current_price_info
        #             items["original_price"] = "$" + str(current_price)
        #             items["current_price"] = "$" + str(current_price)
        #         # size_info = price.get("[data-role=swatch-options]").get("Magento_Swatches/js/swatch-renderer").get("jsonConfig").get("attributes").get("138").get("options")

        items["brand"] = 'carbon38'
        name_info = response.xpath('//div[@class="product_name"]').get()
        if name_info:
            name = self.filter_html_label(name_info)
            items["name"] = name
        # attributes = list()
        # items["attributes"] = attributes
        about_info = response.xpath('//div[@class="data item content"]//p[@class="pdp_tab_box_par"]').get()
        if about_info:
            about = self.filter_html_label(about_info)
            items["about"] = about
        description_info = response.xpath('//div[@class="product attribute description"]//p').get()
        if description_info:
            description = self.filter_html_label(description_info)
            items["description"] = description
        care_info = response.xpath('//div[@id="product.info.fabric"]//div[@class="pdp_tab_box"][last()]').get()
        if care_info:
            care = self.filter_html_label(care_info)
            items["care"] = care
        items["source"] = website
        image_info = response.xpath(
            '//div[@class="product media product-gallery"]//div[@class="gallery"]//ul//li//img/@data-src').getall()
        items["images"] = image_info
        Breadcrumb_info = response.xpath('//li[@class="breadcrumbs-list__item"]/a/text()').getall()
        Breadcrumb_list = list()
        for b in Breadcrumb_info:
            b = self.filter_html_label(b)
            Breadcrumb_list.append(b)
        if Breadcrumb_list:
            items["cat"] = Breadcrumb_list[-1]
            items["detail_cat"] = ''.join(i + '/' for i in Breadcrumb_list)[:-1]
        sku_list = list()
        image_url = response.xpath('//a[@class="show-gallery"]/@href').getall()
        image_url = [response.urljoin(url) for url in image_url]
        items["images"] = image_url


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

        print(items)
        # item_check.check_item(items)
        # detection_main(
        #     items=items,
        #     website=website,
        #     num=self.settings["CLOSESPIDER_ITEMCOUNT"],
        #     skulist=True,
        #     skulist_attributes=True)

        # yield items
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