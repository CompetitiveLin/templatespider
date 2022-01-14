# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class OverseaspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class ShopItem(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    source = scrapy.Field()  # 来自哪个网站
    cat = scrapy.Field()  # 商品类型
    detail_cat = scrapy.Field()  # 详细的类型
    brand = scrapy.Field()  # 品牌
    sales = scrapy.Field()  # 总销量
    attributes = scrapy.Field()  # 商品属性材质列表
    measurements = scrapy.Field()  # 规格尺寸
    total_inventory = scrapy.Field()  # 总货存
    original_price = scrapy.Field()  # 原价
    current_price = scrapy.Field()  # 现价
    about = scrapy.Field()  # 介绍文案
    care = scrapy.Field()  # 保养方式
    sku_list = scrapy.Field()  # SkuItem's list
    images = scrapy.Field()  # 商品图片
    description = scrapy.Field()  # 商品功能描述
    url = scrapy.Field()  # 商品链接
    video = scrapy.Field()  # 商品视频
    is_deleted = scrapy.Field()
    created = scrapy.Field()
    updated = scrapy.Field()
    original_url = scrapy.Field()  # 原始商品链接
    lastCrawlTime = scrapy.Field()
    currency = scrapy.Field()
    site_id = scrapy.Field() # 网站id
    task_id = scrapy.Field() # 任务id



class SkuItem(scrapy.Item):
    attributes = scrapy.Field()  # SkuAttributesItem
    inventory = scrapy.Field()  # 货存
    original_price = scrapy.Field()  # 原价
    current_price = scrapy.Field()  # 现价
    imgs = scrapy.Field()
    sku = scrapy.Field()
    url = scrapy.Field()


class SkuAttributesItem(scrapy.Item):
    colour_img = scrapy.Field()  # 颜色的图片
    colour = scrapy.Field()  # 颜色
    size = scrapy.Field()  # 尺码
    other = scrapy.Field()  # 其他可选择的地方，如沙发是否可折叠啊

sku_validations = {
    'attributes': {
        'can_be_None': False,
        'type': 'dict'
    },
    'inventory': {
        'can_be_None': True,
        'type': 'int'
    },
    'original_price': {
        'can_be_None': False,
        'type': 'str'
    },
    'current_price': {
        'can_be_None': False,
        'type': 'str'
    },
    'imgs': {
        'can_be_None': True,
        'type': 'list_str'
    },
    'sku': {
        'can_be_None': True,
        'type': 'str'
    },
    'url': {
        'can_be_None': True,
        'type': 'str'
    },
}

sku_attr_validations = {
    'colour': {
        'can_be_None': True,
        'type': 'str'
    },
    'size': {
        'can_be_None': True,
        'type': 'str'
    },
    'colour_img': {
        'can_be_None': True,
        'type': 'str'
    },
    'other': {
        'can_be_None': True,
        'type': 'dict'
    },
}