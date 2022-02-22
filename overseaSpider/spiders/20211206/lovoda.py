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

website = 'lovoda'


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
    allowed_domains = ['lovoda.com']
    start_urls = ['https://lovoda.com/']

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
        category_urls = [
            'https://lovoda.com/earrings/',
            'https://lovoda.com/necklaces/',
            'https://lovoda.com/bracelets/',
            'https://lovoda.com/rings/',
            'https://lovoda.com/more-accessories/'
        ]
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[contains(@class,'prod-item')]//div[@class='prod-image']/a/@href").getall()
        # detail_url_list = ['https://lovoda.com/twisted-texture-ring/',
        #                    'https://lovoda.com/heart-organ-bracelet/',
        #                    'https://lovoda.com/crescent-moon-ring/']
        # detail_url_list = ['https://lovoda.com/anchor-bracelet/']
        for detail_url in detail_url_list:
            # print(detail_url)
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-item pagination-item--next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        price_new = response.xpath("//div[@class='productView']//span[@class='price price--withoutTax']/text()").get()
        price_new = price_new.replace("$",'')
        price_old = response.xpath("//div[@class='productView']//span[@class='price price--rrp']/text()").get()
        if price_old:
            price_old = price_old.replace("$",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        name = name.replace('\n','')
        name = name.strip()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li/a/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)
        items["brand"]= ''
        description = response.xpath("//div[@id='tab-description-panel']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//div[@class='productView-thumbnail']/a/@href").getall()
        if images_list:
            items["images"] = images_list
        else:
            return

        opt_name_tmp = response.xpath("//label[@class='form-label form-label--alternate form-label--inlineSmall']/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
            if o.find('Color')!=-1:
                opt_name.append('Color')
            elif o.find('Size')!=-1:
                opt_name.append('Size')
        if not opt_name:
            items["sku_list"] = []
        else:
            select_dict = dict()
            opt_value = []
            opt_length = len(opt_name)
            for i in range(opt_length):
                if opt_name[i]=='Color':
                    value_tmp_value=response.xpath("//option[@data-product-attribute-value]/@value").getall()
                    value_tmp=response.xpath("//option[@data-product-attribute-value]/text()").getall()
                    for j in range(len(value_tmp)):
                        select_dict[value_tmp[j]]=value_tmp_value[j]
                    if value_tmp:
                        opt_value.append(value_tmp)
                if opt_name[i]=='Size':
                    value_tmp = response.xpath("//label[@data-product-attribute-value]/span/text()").getall()
                    if value_tmp:
                        opt_value.append(value_tmp)
            attrs_list = []
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'Size':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                        product_id = response.xpath("//input[@name='product_id']/@value").get()
                        attribute = response.xpath("//select/@name").get()
                        attribute_number = re.search('\d+', attribute).group()
                        attribute_value = select_dict[attr[1]]
                        url = "https://lovoda.com/remote/v1/product-attributes/" + str(product_id)

                        payload = 'action=add&attribute%5B' + str(attribute_number) + '%5D=' + str(
                            attribute_value) + '&product_id=' + str(product_id) + '&qty%5B%5D=1'
                        headers = {
                            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                            'stencil-config': '{}',
                            'X-XSRF-TOKEN': 'eae94684e68d9e3dd135b6c40e797e5d54bcc0136650a1686da447bd5bead1dc',
                            'sec-ch-ua-mobile': '?0',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'Accept': '*/*',
                            'X-Requested-With': 'XMLHttpRequest',
                            'stencil-options': '{}',
                            'sec-ch-ua-platform': '"Windows"',
                            'Sec-Fetch-Site': 'same-origin',
                            'Sec-Fetch-Mode': 'cors',
                            'Sec-Fetch-Dest': 'empty',
                            'Cookie': 'SHOP_SESSION_TOKEN=cdv9kvlp4d03t5v3tue1bboq7p; Shopper-Pref=3F3AF2F54A7A9D334C9D37FD9F63318064B863EE-1638330303615-x%7B%22cur%22%3A%22USD%22%7D; XSRF-TOKEN=7415515a24365aae4aa11fd978de53b002d07b1c3ba30a4b9a759db85b1e229a; fornax_anonymousId=60702e33-dfeb-4189-a506-49e8fe84a855'
                        }

                        response0 = requests.request("POST", url, headers=headers, data=payload)
                        res_json = json.loads(response0.text)
                        img_json = res_json['data']['image']
                        img_list = []
                        if img_json:
                            img = img_json['data']
                            img = img.replace("{:size}","1280x1280")

                            img_list.append(img)
                            sku_info["imgs"] = img_list
                        else:
                            img_list.append(images_list[0])
                            sku_info["imgs"] = img_list
                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
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
        detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
