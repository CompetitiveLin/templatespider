import os
import gzip
import time
import json
import pickle
import logging

from scrapy.spiders import Spider, Request

logger = logging.getLogger(__name__)

class MysqlParseMixin(object):
    pass

class MysqlParseSpider(MysqlParseMixin, Spider):

    @classmethod
    def from_crawler(self, crawler, *args, **kwargs):
        obj = super(MysqlParseMixin, self).from_crawler(crawler, *args, **kwargs)
        return obj

