# -*- coding: utf-8 -*-
import os
import ssl
import time
import pathlib
import logging
import traceback

import pymongo
import platform

from itemadapter import ItemAdapter
# from pybloom_live import ScalableBloomFilter
#
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
from overseaSpider import items
import logging

from overseaSpider.util.item_check import check_item
from overseaSpider.util.utils import isLinux

logger = logging.getLogger(__name__)

class OverseaspiderPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        # 实例化扩展对象
        ext = cls(crawler.settings, crawler)
        # 将扩展对象连接到信号， 将signals.spider_idle 与 spider_idle() 方法关联起来。
        # crawler.signals.connect(ext.spider_idle, signal=signals.spider_idle)
        return ext

    def __init__(self, settings, crawler):
        sysstr = isLinux()
        # 判断是否是linux系统, 如果不是则走本地配置
        if not sysstr:
            # 本地测试存储
            self.connection = pymongo.MongoClient(
                settings['MONGODB_SERVER'],
                settings['MONGODB_PORT']
            )
        else:
            #     f"mongodb://{username}:{password}@{mongo_uri}/?ssl=true&ssl_ca_certs={cert}&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false&w=majority"
            uri = f'mongodb://{settings["MONGODB_USER"]}:{settings["MONGODB_PWD"]}@{settings["MONGODB_URL"]}/?ssl=true&ssl_ca_certs={settings["MONGODB_CERT"]}&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false&w=majority'
            self.connection = pymongo.MongoClient(uri)
            # self.connection = pymongo.MongoClient(uri, ssl_cert_reqs=ssl.CERT_NONE)

        db = self.connection[settings['MONGODB_DB']]
        self.collection = db[settings['MONGODB_COLLECTION']]

        # count
        self.mongocounts = 0
        self.counts = 0
        self.CrawlCar_Num = 1000000
        self.settings = settings

        # bloom file
        filename = str(pathlib.Path.cwd()) + '/blm/' + settings['MONGODB_DB'] + '/' + settings['MONGODB_COLLECTION'] + '.blm'
        dirname = str(pathlib.Path.cwd()) + '/blm/' + settings['MONGODB_DB']

        # 布隆过滤
        # self.df = ScalableBloomFilter(initial_capacity=self.CrawlCar_Num, error_rate=0.01)
        # self.df = BloomFilter(capacity=self.CrawlCar_Num, error_rate=0.01)

        # read
        if os.path.exists(dirname):
            if os.path.exists(filename):
                self.fa = open(filename, "a")
            else:
                pathlib.Path(filename).touch()
                self.fa = open(filename, "a")
        else:
            os.makedirs(dirname)
            pathlib.Path(filename).touch()
            self.fa = open(filename, "a")

        with open(filename, "r") as fr:
            lines = fr.readlines()
            for line in lines:
                line = line.strip('\n')
                self.df.add(line)

    def process_item(self, item, spider):
        check_status = check_item(item)
        if check_status:
            valid = True
            i = item["id"]
            returndf = self.df.add(i)
            if returndf:
                valid = False
                print("Drop data {0}!".format(item["url"]))

            if valid:
                self.fa.writelines(i + '\n')
                # self.collection.insert_one(dict(item))
                self.collection.insert_one(ItemAdapter(item).asdict())
                logger.info(msg=f"scrapy              {self.mongocounts}              items")
                self.mongocounts += 1

    def close_spider(self, spider):
        self.connection.close()
