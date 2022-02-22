# -*- coding: utf-8 -*-
import re
import json
from sys import prefix
import time
from urllib import parse
import scrapy
from hashlib import md5
from overseaSpider.util.utils import isLinux

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

site_name = 'westerlindoutdoor'  # 站名 如 'shopweareiconic'
domain_name = 'westerlindoutdoor.com'  # 完整域名 如 'shopweareiconic.com'
url_prefix = 'https://www.westerlindoutdoor.com'  # URL 前缀 如 'https://shopweareiconic.com'

currency_json_data = None


def convert_currency(price):
    # 这里是个强硬的货币转换（基于 shopify 自己的实时汇率表），部分非美元站点的美元价格是直接这样转来的。慎用，还是优先做美元站吧
    # _from = 'EUR'
    # to = 'USD'
    # return '${:.2f}'.format(price * currency_json_data[_from] / currency_json_data[to])
    # 如无需转换：
    return '{:.2f}'.format(price)


# 把 shopify 格式的 SKU 信息转换成我们的格式，一般不用改
def translate_sku_data(raw_sku_data, options_arr):
    sku_item = SkuItem()
    sku_item['current_price'] = convert_currency(float(raw_sku_data['price']))
    sku_item['original_price'] = convert_currency(float(raw_sku_data['compare_at_price'])) if raw_sku_data[
                                                                                                  'compare_at_price'] and float(
        raw_sku_data['compare_at_price']) != 0 else sku_item['current_price']
    sku_item['imgs'] = [raw_sku_data['featured_image']['src']] if raw_sku_data['featured_image'] else []

    sku_attributes_item = SkuAttributesItem()
    for i in range(3):
        optionTitle = raw_sku_data['option' + str(i + 1)]
        if optionTitle and options_arr[i]:
            optionName = options_arr[i]['name'].strip()
            if 'size' in optionName.lower():
                sku_attributes_item['size'] = optionTitle
            elif 'color' in optionName.lower() or 'colour' in optionName.lower():
                sku_attributes_item['colour'] = optionTitle
            else:
                sku_attributes_item['other'] = {optionName: optionTitle}
    sku_item['attributes'] = sku_attributes_item
    return sku_item


# 尝试从 shopify 的 product_type 字段解析出类目信息的函数
def parse_category_by_product_type(product_type, full):
    separators = [' - ', ' > ', '>']
    for separator in separators:
        if separator in product_type:
            arr = product_type.split(separator)
            arr = list(map(lambda cat: cat.replace("/", "／"), arr))
            if full:
                return '/'.join(arr)
            else:
                return arr[-1]
    return product_type.replace("/", "／")


# 从 SKU 列表中提取出最低现价（最终展示的现价）
def item_display_price(skus):
    min_price = float(skus[0]['price'])
    for sku in skus:
        min_price = min(float(sku['price']), min_price)
    return convert_currency(min_price)


# 从 SKU 列表中提取出最高原价（最终展示的原价）
def item_original_price(skus):
    max_price = 0.0
    for sku in skus:
        if sku['compare_at_price']:
            max_price = max(float(sku['compare_at_price']), max_price)
    return convert_currency(max_price) if max_price > 0 else item_display_price(skus)


# 检测是否不缺货（是否所有 SKU 都有库存）
def item_is_available(skus):
    for sku in skus:
        if bool(sku['available']) and float(sku['price']) > 0:
            return True
    return False


# 解析 attributes 和 description（部分站点需要调整）
def fill_attributes_and_description(shop_item, item_obj):
    body_html = item_obj['body_html']

    if not body_html:
        shop_item["description"] = ''
        return

    body_html = re.sub(r'[\t\n\r\f\v]', ' ', body_html)
    attribute_matches = list(re.finditer(r'(<strong[^><]*>([^><:]+):</strong>([^><]+))<', body_html))
    if len(attribute_matches) > 0:
        shop_item['attributes'] = []
        for match in attribute_matches:
            shop_item['attributes'].append(filter_text(match.group(2).strip() + ": " + match.group(3).strip()))
            body_html = body_html.replace(match.group(1), "")
    shop_item["description"] = filter_text(body_html)


def filter_text(input_text):
    input_text = re.sub(r'<.*?>', ' ', input_text)
    filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                   u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                   u'\u200A', u'\u202F', u'\u205F']
    for index in filter_list:
        input_text = input_text.replace(index, "").strip()
    return re.sub(r'\s+', ' ', input_text)


class ShopweareiconicSpider(scrapy.Spider):
    name = site_name
    allowed_domains = [domain_name]

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            # 'CLOSESPIDER_ITEMCOUNT' : 10,#检测个数
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(ShopweareiconicSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "叶复")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': site_name,
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

    def start_requests(self):
        yield scrapy.Request(url=url_prefix + '/services/javascripts/currencies.js',
                             callback=self.get_currency_rates, )  # 获取汇率转换表

    def get_currency_rates(self, response):
        currency_json_str = re.search(r'rates:\s*(\{.*?\})', response.text).group(1)
        global currency_json_data
        currency_json_data = json.loads(currency_json_str)

        # limit 最大为 250，超过无效，勿改
        yield scrapy.Request(url=url_prefix + '/products.json?page=1&limit=250', callback=self.parse, cookies={
            'cart_currency': 'USD'
        })

    def parse(self, response):

        json_data = json.loads(response.text)
        items_list = list(json_data['products'])

        for item_obj in items_list:
            # 不对劲的商品，直接过滤掉不管
            if not item_is_available(item_obj['variants']) or len(list(item_obj['images'])) == 0:
                continue

            shop_item = ShopItem()

            shop_item["url"] = url_prefix + '/products/' + str(item_obj['handle'])
            shop_item["brand"] = item_obj['vendor']
            shop_item["name"] = item_obj['title']

            shop_item["current_price"] = item_display_price(item_obj['variants'])
            shop_item["original_price"] = item_original_price(item_obj['variants'])

            fill_attributes_and_description(shop_item, item_obj)

            shop_item["source"] = site_name
            img_list = list(map(lambda obj: obj['src'], item_obj['images']))
            ####### 第二个图片做为主图
            # if len(img_list) > 1:
            #     img_list_1 = [img_list[1]]
            #     for i in img_list:
            #         if i not in img_list_1:
            #             img_list_1.append(i)
            #     shop_item["images"] = img_list_1
            # else:
            #     shop_item["images"] = img_list
            ####### 正常
            shop_item["images"] = img_list
            ###############################
            shop_item["sku_list"] = list(
                map(lambda sku: translate_sku_data(sku, item_obj['options']), item_obj['variants']))

            shop_item["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
            status_list = list()
            status_list.append(shop_item["url"])
            status_list.append(shop_item["original_price"])
            status_list.append(shop_item["current_price"])
            status_list = [i for i in status_list if i]
            status = "-".join(status_list)
            shop_item["id"] = md5(status.encode("utf8")).hexdigest()

            shop_item["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            shop_item["created"] = int(time.time())
            shop_item["updated"] = int(time.time())
            shop_item['is_deleted'] = 0

            # 1. 详情页没有类目信息的情况：直接从 product_type 字段解析类目，一般 product_type 会是最细一级类目的名称
            shop_item["cat"] = parse_category_by_product_type(item_obj['product_type'], False)
            shop_item["detail_cat"] = parse_category_by_product_type(item_obj['product_type'], True)

            # 2. 详情页有类目信息的情况，注释掉上面两行，请求详情页，从详情页里解析类目信息
            # requests.get ...

            # yield shop_item
            print('=======')
            print(shop_item)

        if len(items_list) > 0:
            coms = list(parse.urlparse(response.url))
            params = parse.parse_qs(coms[4])
            params['page'] = [int(params['page'][0]) + 1]
            coms[4] = parse.urlencode(params, True)
            next_page_url = parse.urlunparse(coms)

            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                cookies={
                    # 'cart_currency': 'USD'
                }
            )