# -*- coding: utf-8 -*-
import re
import itertools
import json
import time
import scrapy
import requests
from hashlib import md5
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'teegolfclub'
# 全流程解析脚本

class teegolfclub(scrapy.Spider):
    name = website
    # allowed_domains = ['teegolfclub']
    # start_urls = ['https://teegolfclub.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 6
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(teegolfclub, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "流冰")
        self.headers = {'accept': '*/*', 'accept-encoding': 'gzip, deflate, br', 'cache-control': 'no-cache', 'content-length': '66', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'cookie': 'SHOP_SESSION_TOKEN=uv9ebk1uns2004he810t5r3h7u; fornax_anonymousId=ff6ff774-910b-446a-ae29-80b7535a8d07; _ga=GA1.2.526016783.1638095281; _caid=2c402b64-a6d2-4bb5-a878-a8aa160dbfeb; _fbp=fb.1.1638095284822.951651034; XSRF-TOKEN=84a53cf947a488b84f1a0e8a967a3d5f4eadbdc800d7c44e2b1b23fd9b43ffbe; _cavisit=17d73a455d1|; _gid=GA1.2.170805180.1638322690; popupShownOnceAlready=true; STORE_VISITOR=1; _sp_ses.5cc8=*; landing_site=https://teegolfclub.com/; lastVisitedCategory=698; __atuvc=5%7C48; __atuvs=61a6d21ec53e1725000; paypal-offers--view-count-credit%2Cone-touch%2Creturn-shipping%2Cpurchase-protection=3; Shopper-Pref=CE76D9837047E93D30680022D88C082BFC8B8156-1638927669476-x%7B%22cur%22%3A%22USD%22%7D; _sp_id.5cc8=62599fc1e4da1186.1638095282.3.1638322870.1638158657', 'origin': 'https://teegolfclub.com', 'pragma': 'no-cache', 'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36', 'x-requested-with': 'XMLHttpRequest', 'x-xsrf-token': '84a53cf947a488b84f1a0e8a967a3d5f4eadbdc800d7c44e2b1b23fd9b43ffbe'}

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOAD_HANDLERS' :{
            'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler',
        },
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

    def clear_price(self,org_price,cur_price,Symbol='$'):
        """价格处理"""
        if not org_price and not cur_price:
            return None, None
        if org_price and '-' in org_price:
            org_price = org_price.split('-')[0]
        if cur_price and '-' in cur_price:
            cur_price = cur_price.split('-')[0]
        if org_price:
            org_price = str(org_price).replace(Symbol, '').replace(' ', '').replace(',', '.').replace('\n','')
        if cur_price:
            cur_price = str(cur_price).replace(Symbol, '').replace(' ', '').replace(',', '.').replace('\n','')
        org_price = org_price if org_price and org_price != '' else cur_price
        cur_price = cur_price if cur_price and cur_price != '' else org_price
        if org_price.count(".") > 1:
            org_price =list(org_price)
            org_price.remove('.')
            org_price = ''.join(org_price)
        if cur_price.count(".") > 1:
            cur_price =list(cur_price)
            cur_price.remove('.')
            cur_price = ''.join(cur_price)
        return org_price, cur_price

    def product_dict(self,**kwargs):
        # 字典值列表笛卡尔积
        keys = kwargs.keys()
        vals = kwargs.values()
        for instance in itertools.product(*vals):
            yield dict(zip(keys, instance))

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
        for pattern in label_pattern:
            labels = re.findall(pattern, text, re.S)
            for label in labels:
                text = text.replace(label, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

    def filter_text(self, input_text):
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F',u'\u200b']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def remove_space_and_filter(self,l):
        # 洗列表文本
        new_l = []
        for i,j in enumerate(l):
            k = self.filter_html_label(self.filter_text(j))
            if k == '':
                continue
            if not k.strip().endswith('.') and not k.strip().endswith(':') and not k.strip().endswith(','):
                k = k+'.'
            new_l.append(k)
        return new_l

    def start_requests(self):
        #url_list = [
#
        #]
        #for url in url_list:
        #    print(url)
        #    yield scrapy.Request(
        #       url=url,
        #    )

        url = "https://teegolfclub.com/"
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            meta={'h2':True}
        )

    def parse(self, response):
        url_list = [
            'https://teegolfclub.com/clubs/',
            'https://teegolfclub.com/golf-apparel/',
            'https://teegolfclub.com/bags/',
            'https://teegolfclub.com/balls/',
            'https://teegolfclub.com/clearance/',
            'https://teegolfclub.com/accessories/',
            'https://teegolfclub.com/shoes/',
        ]
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta=response.meta
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//figure[@class='card-figure']/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        # url_list = ['https://teegolfclub.com/adidas-codechaos-golf-shoes/']
        for url in url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta=response.meta
            )

        next_page_url = response.xpath("//li[contains(@class,'pagination-item pagination-item--next')]/a/@href").getall()
        if next_page_url:
            next_page_url = next_page_url[0]
            next_page_url = response.urljoin(next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        # price = re.findall("", response.text)[0]
        original_price = response.xpath(
            "//div[@class='productView-price']//span[@class='price price--rrp']//text()").get()
        current_price = response.xpath(
            "//div[@class='productView-price']//span[@class='price price--withoutTax']//text()").get()
        items["original_price"], items["current_price"] = self.clear_price(original_price, current_price)
        if not items["current_price"]:
            return
        items["brand"] = response.xpath('//h2[@class="productView-brand"]//span//text()').get()
        items["name"] = response.xpath("//h1[contains(@class,'productView-title')]/text()").get()
        attributes = response.xpath("//div[@id='tab-description']//li//text()").getall()
        attributes = self.remove_space_and_filter(attributes)
        items["attributes"] = attributes
        items["description"] = response.xpath("//div[@id='tab-description']//p[1]//text()").get()
        items["description"] = self.filter_text(items["description"])
        items["source"] = website
        images_list = response.xpath("//figure[@rel='productImages']/@href").getall()
        items["images"] = images_list

        Breadcrumb_list = response.xpath("//ul[@class='breadcrumbs']//li//a/text()").getall()
        items["cat"] = Breadcrumb_list[-1]
        items["detail_cat"] = '/'.join(Breadcrumb_list)

        sku_list = list()
        sku_options = response.xpath(
            "//div[@class='productView-options']//form[@enctype='multipart/form-data']//div[@data-product-option-change]//div[contains(@class,'field')]")
        sku_dict = {}
        if sku_options:
            for sku_option in sku_options:
                l = []
                # 取sku种类名字
                sku_opt_name = sku_option.xpath(
                    "./label[@class='form-label form-label--alternate form-label--inlineSmall']/text()[last()]").get().strip()
                if sku_opt_name.endswith(":"):
                    sku_opt_name = sku_opt_name[:-1]
                # 取attribute[]值
                sku_opt_attr_name = sku_option.xpath(".//select/@name").get()
                if not sku_opt_attr_name:
                    # 说明选项不是select
                    sku_variant_name_list = sku_option.xpath(".//label[@for]//text()").getall()  # 选项名列表
                    sku_variant_name_list = self.remove_space_and_filter(sku_variant_name_list)
                    if not sku_variant_name_list or len(sku_variant_name_list) == 0:
                        sku_variant_name_list = sku_option.xpath(".//label[@for]/span[1]/@title").getall()
                    # print(sku_variant_name_list)
                    sku_opts = sku_option.xpath(".//input[@value and not(@value='')]")
                    for i, sku_opt in enumerate(sku_opts):
                        # print(i)
                        sku_opt_attr_name = sku_opt.xpath("./@name").get()
                        sku_attr_id = sku_opt.xpath("./@value").get()
                        sku_name = sku_variant_name_list[i]
                        l.append((sku_opt_attr_name, sku_attr_id, sku_name))
                    sku_dict[sku_opt_name] = l
                else:
                    sku_opts = sku_option.xpath(".//option[@value and not(@value='')]")
                    for sku_opt in sku_opts:
                        sku_attr_id = sku_opt.xpath("./@value").get()
                        sku_name = sku_opt.xpath("./text()").get()
                        l.append((sku_opt_attr_name, sku_attr_id, sku_name))
                    sku_dict[sku_opt_name] = l

            org_sku_list = list(self.product_dict(**sku_dict))
            product_id = response.xpath("//div[@class='productView-options']//input[@name='product_id']/@value").get()
            if len(org_sku_list) > 0:
                for sku in org_sku_list:
                    post_url = 'https://teegolfclub.com/remote/v1/product-attributes/{}'.format(product_id)
                    post_data = {
                        'action': 'add',
                        'product_id': product_id,
                        'qty[]': 1
                    }
                    sku_item = SkuItem()
                    other = dict()
                    attributes = SkuAttributesItem()
                    sku_item["url"] = response.url
                    for sku_i in sku.values():
                        post_data[sku_i[0]] = sku_i[1]

                    # import httpx
                    # with httpx.Client(http2=True) as client:
                    #     post_res = client.post(url=post_url,data=post_data)
                    post_res = requests.post(post_url,data=post_data,headers=self.headers)
                    # post_res = yield scrapy.FormRequest(method='POST',url=post_url, body=json.dumps(post_data), headers=self.headers,callback=self.test_post,meta={'h2':True})
                    post_res_json = json.loads(post_res.text)
                    #
                    sku_data = post_res_json["data"]
                    try:
                        org_price = str(sku_data["price"]["rrp_without_tax"]["value"])
                    except:
                        org_price = None
                    cur_price = str(sku_data["price"]["without_tax"]["value"])
                    if not org_price:
                        org_price = cur_price
                    sku_item["original_price"] = str(org_price)
                    sku_item["current_price"] = str(cur_price)
                    sku_item["sku"] = sku_data["sku"]
                    try:
                        img = sku_data['image']["data"]
                        sku_item["imgs"] = [img.replace("{:size}", '1280x1280')]
                    except:
                        pass
                    for k, v in sku.items():
                        other[k] = v[2]
                    attributes["other"] = other
                    sku_item["attributes"] = attributes
                    sku_list.append(sku_item)
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

        print(items)
        # yield items
        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                 skulist_attributes=True)
