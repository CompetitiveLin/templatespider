# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from urllib import parse

website = 'jomashop'

class JomashopSpider(scrapy.Spider):
    name = website
    allowed_domains = ['jomashop.com']
    # start_urls = ['http://jomashop.com/']

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')

    def __init__(self, **kwargs):
        super(JomashopSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "凯棋")

    is_debug = True
    custom_debug_settings = {
        # 'MONGODB_SERVER': '127.0.0.1',
        # 'MONGODB_DB': 'fashionspider',
        # 'MONGODB_COLLECTION': 'fashions_pider',
        'MONGODB_COLLECTION': 'jomashop',
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 0,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ALWAYS_STORE': False,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
        "URLLENGTH_LIMIT": 5000
    }

    def start_requests(self):
        url_list = [
            "https://www.jomashop.com/watches-for-men.html",
            "https://www.jomashop.com/watches-for-women.html",
            "https://www.jomashop.com/watches.html",
            "https://www.jomashop.com/jewelry.html",
            "https://www.jomashop.com/handbags-accessories.html",
            "https://www.jomashop.com/sunglasses.html",
            "https://www.jomashop.com/beauty.html",
            "https://www.jomashop.com/gift-guide.html",
            "https://www.jomashop.com/ladies-mens-apparel.html",
            "https://www.jomashop.com/shoes.html",
            "https://www.jomashop.com/preowned.html",
            "https://www.jomashop.com/new-arrivals.html"
        ]
        for url in url_list:
            yield scrapy.Request(
                url=url,
            )

    def parse(self, response):
        data_id = re.findall('data-model-id="(.*?)" data-model-relative-url', response.text)[0]
        print(data_id)
        url = 'https://www.jomashop.com/graphql?query=query category($id:String!,$pageSize:Int!,$currentPage:Int!,$onServer:Boolean!,$filter:ProductAttributeFilterInput!,$sort:ProductAttributeSortInput){categoryList(filters:{ids:{in:[$id]}}){id description takeshape_intro_description name url_key display_mode landing_page landing_page_identifier breadcrumbs{category_level category_name category_url_key category_url_path __typename}featured_filter children{id level name path url_path url_key __typename}meta_title@include(if:$onServer)meta_keywords@include(if:$onServer)meta_description@include(if:$onServer)canonical_url@include(if:$onServer)filter_map{request_var value_string url __typename}__typename}products(pageSize:$pageSize,currentPage:$currentPage,filter:$filter,sort:$sort){aggregations{attribute_code count label options{label value count swatch_image __typename}__typename}sort_fields{default options{label value __typename}__typename}items{__typename id name msrp price_promo_text promotext_value promotext_type promotext_code stock_status price_range{minimum_price{regular_price{value currency __typename}final_price{value currency __typename}price_promo_text msrp_price{value currency __typename}discount_on_msrp{amount_off percent_off __typename}plp_price{was_price now_price discount promotext_value has_coupon __typename}__typename}__typename}brand_name name_wout_brand manufacturer special_price sku small_image{url sizes{image_id url __typename}__typename}url_key is_preowned}page_info{total_pages current_page __typename}total_count __typename}}&operationName=category&variables={"id":%s,"idNum":%s,"onServer":true,"filter":{"category_id":{"eq":"%s"}},"sort":{},"pageSize":60,"currentPage":1}' % (data_id, data_id, data_id)
        # print(url)
        yield scrapy.Request(
            url=url,
            callback=self.parse_list,
        )

    def parse_list(self, response):
        """列表页"""
        json_data_str = json.loads(response.text)
        products = json_data_str["data"]["products"]
        if products:
            items_list = products["items"]
            for item in items_list:
                stock_status = item["stock_status"]
                if stock_status == "IN_STOCK":
                    url_key = item["url_key"]
                    detail_url = 'https://www.jomashop.com/graphql?query=query productDetail($urlKey:String,$onServer:Boolean!){productDetail:products(filter:{url_key:{eq:$urlKey}}){items{__typename id sku name name_wout_brand on_hand_priority_text on_hand_priority is_preowned brand_name brand_url manufacturer url_key stock_status out_of_stock_template out_of_stock_template_text price_promo_text promotext_code promotext_type promotext_value shipping_availability is_shipping_free_message shipping_question_mark_note model_id image{label url __typename}upc_code item_variation media_gallery{... on ProductImage{label role url sizes{image_id url __typename}url_nocache __typename}__typename}breadcrumbs{path categories{name url_key __typename}__typename}short_description{html __typename}description{html __typename}moredetails{description more_details{group_id group_label group_attributes{attribute_id attribute_label attribute_value __typename}__typename}__typename}msrp price_range{minimum_price{regular_price{value currency __typename}final_price{value currency __typename}price_promo_text msrp_price{value currency __typename}discount_on_msrp{amount_off percent_off __typename}discount{amount_off percent_off __typename}__typename}__typename}... on GroupedProduct{items{qty position product{id sku stock_status name brand_name name_wout_brand manufacturer manufacturer_text is_shipping_free_message shipping_availability url_key is_preowned preowned_item_condition preowned_item_condition_text preowned_box preowned_papers preowned_papers_year preowned_condition_description on_hand_priority_text on_hand_priority shipping_question_mark_note model_id msrp price_range{minimum_price{regular_price{value currency __typename}final_price{value currency __typename}price_promo_text msrp_price{value currency __typename}discount_on_msrp{amount_off percent_off __typename}discount{amount_off percent_off __typename}__typename}__typename}media_gallery{... on ProductImage{label role url sizes{image_id url __typename}url_nocache __typename}__typename}description{html __typename}__typename}__typename}__typename}... on ConfigurableProduct{configurable_options{attribute_code attribute_id id label values{default_label label store_label use_default_value value_index swatch_data{type value... on ImageSwatchData{thumbnail __typename}__typename}__typename}__typename}variants{attributes{code value_index label __typename}product{id brand_name brand_url brand_size manufacturer shipping_availability is_shipping_free_message shipping_question_mark_note name_wout_brand msrp price_promo_text promotext_code promotext_type promotext_value is_preowned model_id on_hand_priority_text on_hand_priority price_range{minimum_price{regular_price{value currency __typename}final_price{value currency __typename}price_promo_text msrp_price{value currency __typename}discount_on_msrp{amount_off percent_off __typename}discount{amount_off percent_off __typename}__typename}__typename}media_gallery{... on ProductImage{label role url sizes{image_id url __typename}url_nocache __typename}__typename}sku stock_status description{html __typename}__typename}__typename}__typename}... on GiftCardProduct{allow_open_amount open_amount_min open_amount_max giftcard_type is_redeemable lifetime allow_message message_max_length giftcard_amounts{value_id website_id website_value attribute_id value __typename}__typename}meta_title@include(if:$onServer)meta_keyword@include(if:$onServer)meta_description@include(if:$onServer)canonical_url@include(if:$onServer)}__typename}}&operationName=productDetail&variables={"urlKey":"%s","onServer":true}' % (url_key)
                    yield scrapy.Request(
                        url=detail_url,
                        callback=self.parse_detail,
                        dont_filter=True
                    )

            response_url = parse.unquote(response.url) # url解码

            split_str = '"currentPage":'
            base_url = response_url.split(split_str)[0]
            page_num = int(response_url.split(split_str)[1].replace("}", ""))+1
            next_page_url = base_url + split_str + str(page_num) + "}"
            # print("下一页:"+next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

        else:
            print("当前页码没数据了")


    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()

        json_data = json.loads(response.text)
        item = json_data["data"]["productDetail"]["items"][0]
        items["url"] = response.urljoin(item["canonical_url"])

        price = item["price_range"]["minimum_price"]["regular_price"]["value"]
        original_price = item["price_range"]["minimum_price"]["msrp_price"]["value"]
        current_price = item["price_range"]["minimum_price"]["final_price"]["value"]
        items["original_price"] = "$"+str(original_price) if original_price else "$"+str(current_price)
        items["current_price"] = "$"+str(current_price) if current_price else "$"+str(original_price)
        items["brand"] = item["brand_name"]
        items["name"] = item["name"]
        # items["about"] = response.xpath("").get()
        items["description"] = item["description"]["html"]
        items["source"] = website
        media_gallery_list = item["media_gallery"]
        images_list = [i["url_nocache"] for i in media_gallery_list]
        items["images"] = images_list

        attribute_list = list()
        more_details_list = item["moredetails"]["more_details"]
        if more_details_list:
            for detail_list in more_details_list:
                group_attributes_list = detail_list["group_attributes"]
                for group_attributes in group_attributes_list:
                    attributes_str = group_attributes["attribute_label"] + ":" + group_attributes["attribute_value"]
                    attribute_list.append(attributes_str)
        items["attributes"] = attribute_list

        breadcrumbs_list = item["breadcrumbs"]["categories"]
        breadcrumbs_list = [i["name"] for i in breadcrumbs_list]
        items["cat"] = breadcrumbs_list[-1]
        items["detail_cat"] = "/".join(breadcrumbs_list)

        sku_list = list()
        if "variants" in item:
            variants_list = item["variants"]

            for variants in variants_list:
                product = variants["product"]
                stock_status = product["stock_status"]
                if stock_status != "OUT_OF_STOCK":
                    attributes_list = variants["attributes"]
                    for attribute in attributes_list:
                        sku_item = SkuItem()
                        attributes = SkuAttributesItem()

                        code = attribute["code"] if "code" in attribute else None
                        if code:
                            if "size" in code:
                                attributes["size"] = attribute["label"].replace("Size: ", "")
                            if "color" in code:
                                attributes["colour"] = attribute["label"]

                        original_price = product["price_range"]["minimum_price"]["msrp_price"]["value"]
                        current_price = product["price_range"]["minimum_price"]["final_price"]["value"]
                        sku_item["original_price"] = "$" + str(original_price) if original_price else "$" + str(current_price)
                        sku_item["current_price"] = "$" + str(current_price) if current_price else "$" + str(original_price)
                        sku_item["url"] = items["url"]
                        sku_item["sku"] = product["sku"]
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
