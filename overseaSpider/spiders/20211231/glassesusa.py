# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main

from lxml import etree
import math
from  overseaSpider.util import item_check

website = 'glassesusa'

class GlassesusaSpider(scrapy.Spider):
    name = website
    allowed_domains = ['glassesusa.com']
    start_urls = ['http://glassesusa.com/']

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
        super(GlassesusaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "涛儿")

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT' : 10,#检测个数
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

    def filter_html_label(self, text):
        html_labels = re.findall(r'<[^>]+>', text)
        for h in html_labels:
            text = text.replace(h, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').replace('\xa0', '').strip()
        return text

    # def start_requests(self):
    #     url_list = [
    #         'https://www.glassesusa.com/progressive-lenses',
    #         'https://www.glassesusa.com/eyeglasses-collection',
    #         'https://www.glassesusa.com/sunglasses',
    #     ]
    #     for url in url_list:
    #         yield scrapy.Request(
    #             url=url,
    #             callback=self.parse_list,
    #         )

    def parse(self, response):
        url_list = [
            'https://www.glassesusa.com/progressive-lenses',
            'https://www.glassesusa.com/eyeglasses-collection',
            'https://www.glassesusa.com/sunglasses',
        ]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )



    def parse_list(self, response):
        """列表页"""
        print(response.text)
        url_list = response.xpath('//a[@class="glassesItem__wrapImage___10y44"]/@href').getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )



    def check_digit(self,L):
        for j in L:
            if j.isdigit() == False:
                return False
        return True

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["source"] = 'glassesusa.com'

        name = response.xpath('//div[@id="sidebar"]//p[@class="baseInfo__name___2-UGV"]//text()').get()
        if name:
            items["name"] = name
        else:
            name = response.xpath('//div[@id="sidebar"]//h1[@class="baseInfo__name___2-UGV"]//text()').get()
            if name:
                items["name"] = name

        current_price = response.xpath('//div[@id="sidebar"]//div[@class="price__priceWrapper___1D3pd"]//span[@data-test-name="specialPrice"]//text()').get()
        if current_price:
            items["current_price"] = '' + str(current_price)
        # else:
        #     current_price = response.xpath('').get()
        #     if current_price:
        #         items["current_price"] = '' + str(current_price)
        else:
            items["current_price"] = ''

        original_price = response.xpath('//div[@id="sidebar"]//div[@class="price__priceWrapper___1D3pd"]//span[@data-test-name="regularPrice"]//text()').get()
        if original_price:
            items["original_price"] = '' + str(original_price)
        elif items["current_price"]:
            items["original_price"] = items["current_price"]
        else:
            items["original_price"] = ''

        # brand = response.xpath('').get()
        # if brand:
        #     items["brand"] = brand

        attributes = list()
        _list = response.xpath('//div[@class="frameDetailsAndMeasurements__data___kcRlA"]')
        k_list = []
        v_list = []
        if _list:
            k_ = _list[0].xpath('./strong/text()').getall()
            v_ = _list[0].xpath('./text()').getall()
            for i in k_:
                if i not in k_list and i != '' and i != ' ':
                    k_list.append(i)
            for j in v_:
                if j not in k_list and j != '' and j != ' ':
                    v_list.append(j)

        if k_list != [] and v_list != []:
            for i in range(len(min(k_list,v_list))):
                key = k_list[i]
                value = v_list[i]
                att = key + value
                att_1 = self.filter_html_label(att)
                if att_1 != '' and att_1 != ' ':
                    attributes.append(att_1)
        att_l = response.xpath('//li[@class="frameDetailsAndMeasurements__measurmentsItem___7OmVN"]//text()').getall()
        if att_l:
            for i in range(0, len(att_l),3):
                k = att_l[i]
                v = att_l[i+2]
                att = k + ':' + v
                att_3 = self.filter_html_label(att)
                if att_3 != '' and att_3 != ' ':
                    attributes.append(att_3)
        if attributes:
            items["attributes"] = attributes



        description_list = response.xpath('//div[@class="collapse__content___17d5b"]//p//text()').getall()
        if description_list:
            description = ' '.join(description_list)
            items["description"] = self.filter_html_label(description)



        images_list = response.xpath('//button[@data-test-name="productImage"]//@src').getall()
        if images_list:
            items["images"] = images_list

        Breadcrumb_list = response.xpath('//div[@class="expBreadCrumbs__path___3IM77"]/span//text()').getall()
        if Breadcrumb_list:
            items["cat"] = Breadcrumb_list[-1]
            detail_cat = Breadcrumb_list[0]
            for i in range(1,len(Breadcrumb_list)):
                detail_cat = detail_cat + '/' + Breadcrumb_list[i]
            items["detail_cat"] = detail_cat

        sku_list = list()

        get_infor = response.xpath('//div[@class="colorSwitcher__container___3Li9w"]//span').getall()
        color_img_list = []
        color_list = []
        for i in get_infor:
            get_color_img = re.findall('background-image:url\((.+?)\)"',i)
            color_img_list.append(get_color_img[0])

            get_color = re.findall('aria-label="Choose color (.+?)"><',i)
            color_list.append(get_color[0])



        new_list = []
        get_sku_list = re.findall('appliedCoupons":"","sku":"(.+?)","name":', response.text)

        # get_sku_list = re.findall(',"url":"\\\u002F(.+?).html","gender"', response.text)
        sku_id_L = []
        for i in get_sku_list:
            if '-'in i:
                L = i.split('-')
                if self.check_digit(L) and i not in sku_id_L:
                    sku_id_L.append(i)
        new_url_list = response.url.split('/')
        for i in range(len(color_list)):
            get_size = new_url_list[3].split('-')
            if '/' in color_list[i]:
                get_color_1 = color_list[i].replace(' / ','').replace('Beige','neutrals').replace(' ', '')
            else:
                get_color_1 = color_list[i].replace(' ', '-')
            new_url = 'https://' + new_url_list[2] + '/' + get_color_1 + '-' + get_size[-1] +'/'+ new_url_list[4] + '/'+sku_id_L[i] + '.html'
            new_list.append(new_url.lower())
        for i in range(len(new_list)):
            new_response = requests.get(new_list[i].lower())
            html = etree.HTML(new_response.text, parser=etree.HTMLParser(encoding="utf-8"))
            img_list = html.xpath('//button[@data-test-name="productImage"]//@src')
            get_size_list = response.xpath('//div[@data-test-name="sizeSwitcher"]/span//text()').getall()
            size_list = []
            if get_size_list:
                for j in get_size_list:
                    if j == '' or j == ' ':
                        break
                    size_list.append(j)
            if size_list:
                for size in size_list:
                    '''SkuAttributesItem'''
                    SAI = SkuAttributesItem()
                    SAI["colour_img"] = color_img_list[i]
                    SAI['colour'] = color_list[i]
                    SAI['size'] = size
                    SI = SkuItem()
                    SI['attributes'] = SAI
                    if img_list:
                        SI['imgs'] = img_list
                    else:
                        SI['imgs'] = items["images"]
                    SI['url'] = items['url']
                    SI['original_price'] = items['original_price']
                    SI['current_price'] = items['current_price']
                    sku_list.append(SI)
            else:
                '''SkuAttributesItem'''
                SAI = SkuAttributesItem()
                SAI["colour_img"] = color_img_list[i]
                SAI['colour'] = color_list[i]
                SI = SkuItem()
                SI['attributes'] = SAI
                if img_list:
                    SI['imgs'] = img_list
                else:
                    SI['imgs'] = items["images"]
                SI['url'] = items['url']
                SI['original_price'] = items['original_price']
                SI['current_price'] = items['current_price']
                sku_list.append(SI)


        items["sku_list"] = sku_list
        try:
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
            # print('=============')
            print(items)
            # item_check.check_item(items)
            # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True, skulist_attributes=True)
            # yield items
        except:
            pass

