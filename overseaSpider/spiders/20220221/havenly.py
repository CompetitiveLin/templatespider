# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from lxml import etree

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'havenly'

class havenlySpider(scrapy.Spider):
    name = website
    start_urls = ['https://havenly.com/']
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
        super(havenlySpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "若白")


    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT':5,
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 10,
        'DOWNLOAD_DELAY': 3,
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
        # print('text',text)
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
        category_urls1 = [
            'https://havenly.com/shop/furniture',
            'https://havenly.com/shop/decor-pillows',
            'https://havenly.com/shop/rugs',
            'https://havenly.com/shop/lighting',
        ]
        for category_url in category_urls1:
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_list,

            )
    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath('//a[@class="ShopProductCard_ShopProductCard__qZg7s"]/@href').getall()
        if  len(detail_url_list)==0:
            return
        # print("商品链接",detail_url_list)
        for detail_url in detail_url_list:
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail,

            )
        next_page_url=response.xpath('//a[@rel="next"]/@href').get()
        if next_page_url:
            yield scrapy.Request(
                url='https://havenly.com'+next_page_url,
                callback=self.parse_list,
            )
    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        bd=re.search('"brand":"(.*?)"',response.text,re.S)
        items['brand']=bd.group(1)
        ne = response.xpath('//h1[contains(@class,"product-title")]/text()').get()
        items['name'] = ne.replace('\n', '').strip()
        current_price = response.xpath('//span[@class="h3 mb-0 font-weight-light undefined"]/text()').get()
        isor=response.xpath('//span[@class="h3 mb-0 font-weight-light text-muted"]/s/text()').get()
        if isor:
            items["original_price"] = isor.replace('$', '').replace(',', '').strip()
        else:
            items["original_price"] =current_price.replace('$', '').replace(',', '').strip()
        items["current_price"] = current_price.replace('$', '').replace(',', '').strip()
        da=response.xpath('//div[contains(@class,"ProductSidebar_o-product-sidebar")]/div/a/span/text()').getall()
        items["cat"]=da[-1]
        items["detail_cat"] = self.filter_text(self.filter_html_label('/'.join(da)))
        aboutinfo = response.xpath('//div[@class="product-details"]/p//text()').getall()
        items["about"] = self.filter_text(self.filter_html_label(''.join(aboutinfo)))
        items["source"] = website
        de = response.xpath('//span[@data-test="product-details_description_content"]//text()').getall()
        # de2 = response.xpath('//div[@id="tab-description"]/p/ul/li/text()').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(de)))
        items["images"] = []
        imgs = response.xpath('//ul[contains(@class,"ImageCarousel_CarouselDotListLeft")]/button/img/@src'
                              ).getall()
        for i in list(imgs):
            items['images'].append(i.replace('x60','x1200'))
        if not imgs:
            items['images'].append(response.xpath('//meta[@property="og:image"]/@content').get())
        items["sku_list"] = []
        if 1:
            dadava = response.xpath('//form[@class="variations_form cart"]/@data-product_variations').get()
            # print(dadava)

            # selop=response.xpath('//div[@class="variations"]/div/select/option/text()').getall()[1:]
            # print(selop)
            # if ' ' in selop[0]:
            #     firt="-".join([ i[0].lower()+i[1:] for i in selop[0].split(' ')])
            # else:
            #     firt=selop[0][0].lower()+selop[0][1:]
            # print('sss',firt)
            if dadava:
                # print(json.loads(dadava))
                for i in list(json.loads(dadava)):
                    skuitem = SkuItem()
                    skuatt = SkuAttributesItem()
                    # skuatt['colour'] = i['options'][0]['label']
                    typpp=list(i["attributes"].keys())
                    for j in typpp:
                        if "size" in j:
                            skuatt['size']=i["attributes"][j]
                        if "color" in j:
                            skuatt['colour'] = i["attributes"][j]
                        if "color" not in j and "size" not in j:
                            if  "other" not in list(skuatt.keys()):
                                skuatt['other']={j.split("_")[-1]:i["attributes"][j]}
                            else:
                                d2={j.split("_")[-1]:i["attributes"][j]}
                                skuatt['other'].update(d2)
                    # if "attribute_pa_size" in typpp:
                    #     skuatt['size'] = i["attributes"]["attribute_pa_size"]
                    # if "attribute_pa_color" in typpp:
                    #     skuatt['colour'] = i["attributes"]["attribute_pa_color"]
                    # if "attribute_pa_tabletas" in typpp:
                    #     skuatt['other'] ={"attribute_pa_tabletas":i["attributes"]["attribute_pa_tabletas"]}
                    # if "attribute_pa_capsulas" in typpp:
                    #     skuatt["other"] = {"attribute_pa_capsulas": i["attributes"]["attribute_pa_capsulas"]}
                    # if "attribute_pa_microgramos" in typpp:
                    #     skuatt["other"]={"attribute_pa_microgramos":i["attributes"]["attribute_pa_microgramos"]}
                    # if  not skuatt:
                    #     typppp=list(i["attributes"].keys())[-1]
                    #     skuatt["other"]={typppp:list(i["attributes"].values())[-1]}
                    skuitem["attributes"] = skuatt
                    skuitem["current_price"] = str(i["display_price"])
                    skuitem["original_price"] = str(i["display_regular_price"])
                    items["sku_list"].append(skuitem)

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
        # detection_main(items=items,
        #                website=website,
        #                 num=self.settings['CLOSESPIDER_ITEMCOUNT'],
        #                 skulist=False,
        #                 skulist_attributes=False)
        # print(items)
        yield items







