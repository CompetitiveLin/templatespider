# -*- coding: utf-8 -*-
import re
import json
from sys import prefix
import time
from urllib import parse
import scrapy
import requests
from hashlib import md5
from overseaSpider.util.utils import isLinux

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

site_name = 'franceandson'
domain_name = 'franceandson.com'
url_prefix = 'https://franceandson.com'


def translate_sku_data(raw_sku_data, options_arr):
    sku_item = SkuItem()
    sku_item['current_price'] = '$' + raw_sku_data['price']
    sku_item['original_price'] = ('$' + raw_sku_data['compare_at_price']) if raw_sku_data['compare_at_price'] and float(
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


def parse_category_by_product_type(product_type, full):
    separators = [' - ', ' > ', '>']
    for separator in separators:
        if separator in product_type:
            arr = product_type.split(separator)
            arr = list(map(lambda cat: cat.replace("/", "&"), arr))
            if full:
                return '/'.join(arr)
            else:
                return arr[-1]
    return product_type


def parse_category_by_tags(tags):
    prefixes = ['type-', '__cat:', 'custom-category-']
    for tag in tags:
        for prefix in prefixes:
            if tag.lower().startswith(prefix):
                return tag[len(prefix):]
    return ''


def item_display_price(skus):
    min_price = float(skus[0]['price'])
    for sku in skus:
        min_price = min(float(sku['price']), min_price)
    return '${:.2f}'.format(min_price)


def item_original_price(skus):
    max_price = 0.0
    for sku in skus:
        if sku['compare_at_price']:
            max_price = max(float(sku['compare_at_price']), max_price)
    return '${:.2f}'.format(max_price) if max_price > 0 else item_display_price(skus)


def item_is_available(skus):
    for sku in skus:
        if bool(sku['available']) and float(sku['price']) > 0:
            return True
    return False


def fill_attributes_and_description(shop_item, item_obj):
    body_html = item_obj['body_html']

    if not body_html:
        shop_item["description"] = ''
        return

    body_html = re.sub(r'[\t\n\r\f\v]', ' ', body_html)
    attribute_matches = list(re.finditer(r'(<li[^><]*>([^><:]+):([^><]+))<', body_html))
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


class FranceandsonSpider(scrapy.Spider):
    name = site_name
    allowed_domains = [domain_name]

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
        super(FranceandsonSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "彦泽")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': site_name,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
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
        yield scrapy.Request(url=url_prefix + '/products.json?page=1&limit=250')  # limit 最大为 250，超过无效

    def parse(self, response):
        json_data = json.loads(response.text)
        items_list = list(json_data['products'])

        for item_obj in items_list:

            if not item_is_available(item_obj['variants']):
                continue

            shop_item = ShopItem()

            shop_item["url"] = url_prefix + '/products/' + str(item_obj['handle'])
            shop_item["current_price"] = item_display_price(item_obj['variants'])
            shop_item["original_price"] = item_original_price(item_obj['variants'])
            shop_item["brand"] = item_obj['vendor']
            shop_item["name"] = item_obj['title']

            # shop_item["cat"] = parse_category_by_tags(item_obj['tags'])
            shop_item["cat"] = parse_category_by_product_type(item_obj['product_type'], False)
            # shop_item["detail_cat"] = parse_category_by_tags(item_obj['tags'])
            shop_item["detail_cat"] = parse_category_by_product_type(item_obj['product_type'], True)
            fill_attributes_and_description(shop_item, item_obj)
            shop_item["source"] = site_name
            shop_item["images"] = list(map(lambda obj: obj['src'], item_obj['images']))
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
            print(shop_item)
            # yield shop_item

        if len(items_list) > 0:
            coms = list(parse.urlparse(response.url))
            params = parse.parse_qs(coms[4])
            params['page'] = [int(params['page'][0]) + 1]
            coms[4] = parse.urlencode(params, True)
            next_page_url = parse.urlunparse(coms)

            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
            )
