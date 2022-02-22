# -*- coding: utf-8 -*-
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'hearthsong'
website_url = 'https://www.hearthsong.com'

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
    allowed_domains = ['hearthsong.com']
    start_urls = ['https://www.hearthsong.com/']

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
        category_urls = ['/en/shop-all-outdoor-play/c/8685',
                         '/en/shop-all-indoor-play/c/8680',
                         '/en/education-%26-learning/education-%26-learning/c/8673',
                         '/en/category/arts%2c-crafts-%26-hobbies/c/8331',
                         '/en/category/kids-rooms/c/8532',
                         '/en/category/holidays-%26-celebrations/christmas-%26-hanukkah/c/8383']
        cat = ['Outdoor Play',
               'Indoor Play',
               'Education & Learning',
               'Arts & Crafts',
               'Kids Décor',
               'Christmas & Hanukkah']
        cat_dict = dict()
        for i in range(len(category_urls)):
            category_urls[i] = website_url + category_urls[i]
            cat_dict[category_urls[i]]=cat[i]
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list,meta={'cat':cat_dict[category_url]})

    def parse_list(self, response):
        """商品列表页"""
        cat = response.meta.get('cat')
        detail_url_list = response.xpath("//div[@class='product-item']/div/a[@class='image']/@href").getall()
        for detail_url in detail_url_list:
            detail_url = website_url+detail_url
            yield scrapy.Request(url=detail_url, callback=self.parse_detail, meta={'cat':cat})
        next_page_url = response.xpath("//li[@class='pagination-next']/a[@rel='next']/@href").get()
        if next_page_url:
            next_page_url = website_url + next_page_url
            yield scrapy.Request(url=next_page_url, callback=self.parse_list,meta={'cat':cat})

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        o_cat = response.meta.get('cat')
        price_new = response.xpath("//span[@class='product-details-price__prices']/h2[contains(@class,'price')]/text()").get()
        price_new = price_new.replace("\n", '')
        price_new = price_new.replace(" ", '')
        price_new = price_new.replace("$", '')
        price_old = response.xpath("//span[@class='product-details-price__prices']/h2[contains(@class,'strikethrough-price')]/text()").get()
        if price_old:
            price_old = price_old.replace("\n",'')
            price_old = price_old.replace(" ",'')
            price_old = price_old.replace("$",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new
        items['brand'] = 'HearthSong'
        name = response.xpath("//div[contains(@class,'product-details')]/h1/div[@class='name']/text()").get()
        items["name"] = name

        cat_list = [o_cat,name]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@id='plh-product-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//img[@class='gallery-image']/@src").getall()
        if not images_list:
            images_list = response.xpath("//img[@id='product-image']/@src").getall()
        for i in range(len(images_list)):
            images_list[i] = website_url + images_list[i]
        items["images"] = images_list

        opt_name_tmp = response.xpath("//div[@class='variant-name']/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
            if o.find("Color")!=-1 or o.find("Style")!=-1:
                opt_name.append("Color")
            if o.find("Size")!=-1:
                opt_name.append("Size")
        if not opt_name:
            items["sku_list"] = []
        else:
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            img_dict = dict()
            img_list_tmp = response.xpath("//div[@class='yCmsComponent yComponentWrapper variant-selector clearfix']/div//ul/li/a/img/@src").getall()
            color_list = response.xpath("//div[@class='yCmsComponent yComponentWrapper variant-selector clearfix']/div[1]//ul/li/a/node()/@title").getall()
            for i in range(len(color_list)):
                img_list_tmp[i] = website_url+img_list_tmp[i]
                img_dict[color_list[i]]=img_list_tmp[i]
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='yCmsComponent yComponentWrapper variant-selector clearfix']/div["+str(i+1)+"]//ul/li/a/node()/@title").getall()

                if value_temp:
                    opt_value.append(value_temp)
            # print(opt_value)
            attrs_list = []
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
            # print(attrs_list)

            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()
                img_list = []
                for attr in attrs.items():
                    if attr[0] == 'Size':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color' :
                        sku_attr["colour"] = attr[1]
                        img_list.append(img_dict[attr[1]])
                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["attributes"] = sku_attr



                sku_info["imgs"] = img_list

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
        # print(items)
        yield items
