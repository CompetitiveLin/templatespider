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
from bs4 import BeautifulSoup
website = 'toctockids'
list_sku=[]

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
    allowed_domains = ['toctockids.com']
    start_urls = ['https://toctockids.com/']

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
        category_urls = response.xpath("//ul[@data-depth='1']/li/a[@class='mm-listitem__text']/@href").getall()
        for category_url in category_urls:
            if category_url.find('http')!=-1:
                yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='product-list-images-container']/a/@href").getall()
        # detail_url_list = [
        #     'https://toctockids.com/en/kids-beds/connect-bed-hay/10255-26205.html'
        # ]
        if detail_url_list:
            for detail_url in detail_url_list:
                yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@rel='next']/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url


        price_new = response.xpath("//span[@itemprop='price']/@content").get()
        price_old = response.xpath("//form/div/div/span[@class='regular-price']/text()").get()
        if price_old:
            price_old = price_old.replace('EUR', '')
            price_old = "".join(price_old.split())
            price_old = price_old.replace(",",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1[@itemprop]/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ol/li/a/span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@itemprop='description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//ul[@class='product-images-cover slider-for']/li[@class='cover-container']/img/@src").getall()
        if not images_list:
            return
        items["images"] = images_list

        brand= response.xpath("//span[@class='product_brand']/text()").get()
        if brand:
            items["brand"] = brand
        else:
            items["brand"] = ''
        opt_name = response.xpath("//div[@class='product-variants']/div/div[@class='cselect']/input/@placeholder").getall()

        if not opt_name:
            items["sku_list"] = []
        else:
            opt_value = []
            product_id = response.xpath("//input[@id='product_page_product_id']/@value").get()
            # print(opt_name)
            opt_length = len(opt_name)
            sku_item_list = dict()
            for i in range(opt_length):
                sku_item = dict()
                select_name = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/@name").get()
                value_dict=dict()
                value_temp = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/@title").getall()
                value_value = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/@value").getall()
                if value_temp:
                    opt_value.append(value_temp)
                for v in range(len(value_value)):
                    value_dict[value_temp[v]]=value_value[v]
                sku_item['name']=select_name
                sku_item['value_dict']=value_dict
                sku_item_list[opt_name[i]]=sku_item
            # print(sku_item_list)
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

                for attr in attrs.items():
                    if sku_item_list[attr[0]]['name']=="group[16]":
                        sku_attr["size"] = attr[1]
                    elif sku_item_list[attr[0]]['name']=="group[4]":
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                headers = {
                    'authority': 'toctockids.com',
                    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                    'accept': 'application/json, text/javascript, */*; q=0.01',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'x-requested-with': 'XMLHttpRequest',
                    'sec-ch-ua-mobile': '?0',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                    'sec-ch-ua-platform': '"Windows"',
                    'origin': 'https://toctockids.com',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                    'cookie': 'PrestaShop-e3c4c22f06bbe1db7f61ef031c65e414=def502009224023680422acd694b479d9818b63cdb2c622b5653548d0d66f6887bdc903e3081071bf58cd86e080d1fdc217c919aeccc9af144d1b4196a5c066cc955384dd6e9e8fbb2c5f373c55409f672af48336b94c8d9b8a860e4db079dad8a6e5d798910bc5ee3c2d5113777e7d7abb5ef9caecce44b2d79a4e2923ff9e96248e72566b99731f8ab7e1bd3d5f7c9b1519cfa8475597a9dcdc6351e86c364ac0434bee933ecf131e50eca7c28088e80caa17ec128f57a8cc547acd6254286a49de88f97b85a2f98f32bff28ebbabde9a44a39561d2e30b9; _ga=GA1.2.349982706.1636942945; _pin_unauth=dWlkPVpEWXhNak0xTkRRdE5ESXlZeTAwTUdZeExXRTFZV0l0TlRka1lqbGhaV1JrWTJGaw; _ym_d=1636942948; _ym_uid=1636942948782015667; lsc_private=670b242ee220cba9d3e04add5323bd53; _lscache_vary=lang~2~; _gid=GA1.2.1412446144.1637826215; _ym_isad=1; _ym_visorc=w; PHPSESSID=11h3ea3lfthjuvngiukb1tp353; _uetsid=653386404dc311eca782135997e5cf87; _uetvid=df1cdd9045ba11ecb0224f184716b7e2; idxcookiesWarningCheck={%22accepted%22:true%2C%22banned%22:[]%2C%22date%22:%222021-11-25%2008:45:53%22}; PrestaShop-9d27e315a40a7e0ee84b83b1e276a6bf=def50200fc58e048f662aeaae83f9f9684da4e332a5e0979064081507d91767306fed76dfa909ab0efc0f6ca8d75b180aca99f39f7fb90dc302514b085c013d1d00cd0d7063a98f130e6d621ec49cf38346eca1380533362a39934301129c5789a15154e9d26fea1251e87f8d61d8e063d7c691c2ecd2264b5b4776ca8d1304440cf7797e836aa5ec4b5f84d938b150f704c00f13422c50f08255682913fdc8f1db0b94bcd4db22b7a2c1730a273cfb31ce93552ccb3fc139fb8e6291769799d60300dc5f1fef0a061c3adff8a5a4e4caa072754c00249b3f23a84c9e13247dde9050e122ac06c61a4c1829addaeebb7ef3c66a0c9d51da94b2b6757e47394c9386e785eb91157d21b0ca8',
                }

                params = {
                    'controller': 'product',
                    'token': '2c1fa73836be99f68dd1f60f2ba41bb6',
                    'id_product': str(product_id),
                    'id_customization': '0',
                }
                data = {
                    'quickview': '0',
                    'ajax': '1',
                    'action': 'refresh'
                }
                for attr in attrs.items():
                    params[sku_item_list[attr[0]]['name']]=str(sku_item_list[attr[0]]['value_dict'][attr[1]])
                response0 = requests.post('https://toctockids.com/en/index.php', headers=headers, params=params,
                                         data=data)
                json_str = json.loads(response0.text)
                product_price = json_str['product_prices']
                product_cover_thumbnails = json_str['product_cover_thumbnails']
                soup = BeautifulSoup(product_price, 'lxml')
                # print(soup.span['content'])
                soup1 = BeautifulSoup(product_cover_thumbnails, 'lxml')
                img_list_res = []
                img_list = soup1.select("li[class='thumb-container'] img")
                for i in img_list:
                    # print(i.get('data-image-large-src'))
                    img_list_res.append(i.get('data-image-large-src'))

                if price_old:
                    price_old_list = soup.select('.regular-price')
                    price_old1 = price_old_list[0].string
                    price_old1 = price_old1.replace("EUR", "")
                    price_old1 = price_old1.replace(",", '')
                    price_old1 = price_old1.strip()
                    price_new_list = soup.select('span[itemprop="price"]')
                    price_new1 = price_new_list[0].string
                    price_new1 = price_new1.replace("EUR", "")
                    price_new1 = price_new1.strip()
                    sku_info["current_price"] = str(price_new)
                    sku_info["original_price"] = str(price_old)
                else:
                    sku_info["current_price"] = str(soup.span['content'])
                    sku_info["original_price"] = str(soup.span['content'])
                sku_info["attributes"] = sku_attr
                sku_info["imgs"] = img_list_res


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
        # sku = response.xpath("//div[@class='product-variants']/div").get()
        # if sku:
        #     print(items)
        #     list_sku.append(1)
        #     print(len(list_sku))
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
