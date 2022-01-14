#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import random
import requests
import platform
import traceback
from selenium import webdriver
from scrapy.http import HtmlResponse
from selenium.webdriver import FirefoxProfile

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.python import global_object_name
from scrapy.utils.response import response_status_message
from twisted.internet.error import TimeoutError

import gzip
import logging
import os
import pickle
from email.utils import mktime_tz, parsedate_tz
from importlib import import_module
from weakref import WeakKeyDictionary

from w3lib.http import headers_raw_to_dict, headers_dict_to_raw

from scrapy.http import Headers, Response
from scrapy.responsetypes import responsetypes
from scrapy.utils.httpobj import urlparse_cached
from scrapy.utils.project import data_path
from scrapy.utils.python import to_bytes, to_unicode
from scrapy.utils.request import request_fingerprint

import logging

from overseaSpider.util.utils import isLinux

logger = logging.getLogger(__name__)


# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy import signals


class DummyPolicy:

    def __init__(self, settings):
        self.ignore_schemes = settings.getlist('HTTPCACHE_IGNORE_SCHEMES')
        self.ignore_http_codes = [int(x) for x in settings.getlist('HTTPCACHE_IGNORE_HTTP_CODES')]

    def should_cache_request(self, request):
        return urlparse_cached(request).scheme not in self.ignore_schemes

    def should_cache_response(self, response, request):
        status = response.status not in self.ignore_http_codes
        if not status:
            return status
        # 如果"cache-control"为False则不缓存
        elif "cache-control" in request.meta:
            if not request.meta["cache-control"]:
                status = False

        return status

    def is_cached_response_fresh(self, cachedresponse, request):
        return True

    def is_cached_response_valid(self, cachedresponse, response, request):
        return True

class FilesystemCacheStorage(object):

    def __init__(self, settings):
        self.cachedir = data_path(settings['HTTPCACHE_DIR'])
        self.expiration_secs = settings.getint('HTTPCACHE_EXPIRATION_SECS')
        self.use_gzip = settings.getbool('HTTPCACHE_GZIP')
        self._open = gzip.open if self.use_gzip else open

    def open_spider(self, spider):
        logger.debug("Using filesystem cache storage in %(cachedir)s" % {'cachedir': self.cachedir},
                     extra={'spider': spider})

    def close_spider(self, spider):
        pass

    def retrieve_response(self, spider, request):
        """Return response if present in cache, or None otherwise."""
        metadata = self._read_meta(spider, request)
        if metadata is None:
            return  # not cached
        rpath = self._get_request_path(spider, request)
        with self._open(os.path.join(rpath, 'response_body'), 'rb') as f:
            body = f.read()
        with self._open(os.path.join(rpath, 'response_headers'), 'rb') as f:
            rawheaders = f.read()
        url = metadata.get('response_url')
        status = metadata['status']
        headers = Headers(headers_raw_to_dict(rawheaders))
        respcls = responsetypes.from_args(headers=headers, url=url)
        response = respcls(url=url, headers=headers, status=status, body=body)
        return response

    def store_response(self, spider, request, response):
        """Store the given response in the cache."""
        rpath = self._get_request_path(spider, request)
        if not os.path.exists(rpath):
            os.makedirs(rpath)
        metadata = {
            'url': request.url,
            'method': request.method,
            'status': response.status,
            'response_url': response.url,
            'timestamp': time.time(),
        }
        with self._open(os.path.join(rpath, 'meta'), 'wb') as f:
            f.write(to_bytes(repr(metadata)))
        with self._open(os.path.join(rpath, 'pickled_meta'), 'wb') as f:
            pickle.dump(metadata, f, protocol=2)
        with self._open(os.path.join(rpath, 'response_headers'), 'wb') as f:
            f.write(headers_dict_to_raw(response.headers))
        with self._open(os.path.join(rpath, 'response_body'), 'wb') as f:
            f.write(response.body)
        with self._open(os.path.join(rpath, 'request_headers'), 'wb') as f:
            f.write(headers_dict_to_raw(request.headers))
        with self._open(os.path.join(rpath, 'request_body'), 'wb') as f:
            f.write(request.body)

    def _get_request_path(self, spider, request):
        key = request_fingerprint(request)
        return os.path.join(self.cachedir, spider.name, key[0:2], key)

    def _read_meta(self, spider, request):
        rpath = self._get_request_path(spider, request)
        metapath = os.path.join(rpath, 'pickled_meta')
        if not os.path.exists(metapath):
            return  # not found
        mtime = os.stat(metapath).st_mtime
        if 0 < self.expiration_secs < time.time() - mtime:
            return  # expired
        with self._open(metapath, 'rb') as f:
            return pickle.load(f)


class OverseaspiderSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class OverseaspiderDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class OverseaspiderProxyMiddleware(object):
    def process_request(self, request, spider):
        sys = isLinux()
        if not sys:
            proxy = external_getProxy()
        else:
            proxy = getProxy()
        request.meta['proxy'] = "http://" + proxy
        # print(request.headers)
        print(f'proxy success : {proxy}!')
        # return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.
        # if response.status == 403:
        #     request.meta['proxy'] = "http://" + getProxy()
        #     print('proxy success !')
        #     return request
        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response


def external_getProxy():
    url = 'http://52.200.215.145:5000/'
    headers = {
        'Connection': 'close',
    }
    proxy = requests.get(url, headers=headers, auth=('admin', 'mogu123456')).text
    return proxy


def getProxy():

    url = 'http://172.31.255.158:5000'
    headers = {
        'Connection': 'close',
    }
    proxy = requests.get(url, headers=headers, auth=('admin', 'mogu123456')).text
    return proxy

class OverseaspiderUserAgentMiddleware(UserAgentMiddleware):
    def process_request(self, request, spider):
        ua = random.choice(user_agent_list)
        request.headers.setdefault('User-Agent', ua)


user_agent_list = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    ]

class PhantomjsUpdateCookieMiddleware(object):

    def __init__(self):
        # self.jars = defaultdict(CookieJar)
        root_path = os.path.dirname(os.path.abspath(__file__))
        print(root_path)
        # ----------------------------- PhantomJSDriver -----------------------------
        # 使用无头浏览器
        # self.driver = webdriver.PhantomJS(executable_path=phantomjs_path, service_log_path=os.path.devnull)
        # self.driver = webdriver.PhantomJS(service_log_path=os.path.devnull)
        # # 窗口最大化
        # self.driver.maximize_window()

        # ----------------------------- FirefoxDriver -----------------------------
        # profile = FirefoxProfile()
        # options = webdriver.FirefoxOptions()
        # # options.add_argument('--headless')
        # # 去掉提示：Chrome正收到自动测试软件的控制
        # options.add_argument('disable-infobars')
        # # 修改页面加载策略
        # # self.driver = webdriver.Firefox(firefox_profile=profile, firefox_options=options, executable_path='/usr/bin/firefox')
        # self.driver = webdriver.Firefox(firefox_profile=profile, firefox_options=options)

        # ----------------------------- ChromeDriver -----------------------------
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('disable-infobars')
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=options)

        with open(os.path.join(root_path+"/webdriver/stealth.min.js")) as f:
            js = f.read()
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": js
        })

        # windows = self.driver.window_handles
        # self.driver.switch_to.window(windows[-1])


    def process_request(self, request, spider):
        # if spider.name in [""]:
            # self.driver.implicitly_wait(20)  # 设置等待20秒钟
            # self.driver.get(request.url)
            # body = self.driver.page_source
            # dictCookies = self.driver.get_cookies()
            # cookies = {cookie["name"]: cookie["value"] for cookie in dictCookies}
            # print(cookies)
            # cookiejarkey = request.meta.get("cookiejar")
            # jar = self.jars[cookiejarkey]
            # for cookie in cookies:
            #     jar.set_cookie_if_ok(cookie, request)
            # jar.add_cookie_header(request)
            # self._debug_cookie(request, spider)
            # return HtmlResponse(self.driver.current_url, body=body, encoding='utf-8', request=request)

        self.driver.get(request.url)
        body = self.driver.page_source
        return HtmlResponse(self.driver.current_url, body=body, encoding='utf-8', request=request)

        # return None

    def process_response(self, request, response, spider):
        # if spider.name in ["wayfair"]:
        #     if "sf-ui-header::WEBPACK_ENTRY_DATA" not in response.text:
        #         print(request.url)
        #         print("*"*100)
        #         self.driver.get(request.url)
        #         body = self.driver.page_source
        #         dictCookies = self.driver.get_cookies()
        #         cookies = {cookie["name"]: cookie["value"] for cookie in dictCookies}
        #         # extract cookies from Set-Cookie and drop invalid/expired cookies
        #         # cookiejarkey = request.meta.get("cookiejar")
        #         # jar = self.jars[cookiejarkey]
        #         #
        #         # for cookie in dictCookies:
        #         #     jar.set_cookie_if_ok(cookie, request)
        #         #
        #         # jar.extract_cookies(response, request)
        #         # self._debug_set_cookie(response, spider)
        #         print(body)
        #         request.meta["cookies"] = cookies
        #         return HtmlResponse(self.driver.current_url, body=body, encoding='utf-8', request=request)
        # print("*"*100)
        # print(response.status)
        # if response.status in [503]:
        #     print("-"*100)
        #     self.driver.get(request.url)
        #     time.sleep(10)
        #     body = self.driver.page_source
        #     print(body)
        #     cookies = self.driver.get_cookies()
        #     print(cookies)
        #     c = self.driver.get_cookie("csrftoken")
        #     print(c)
        #     print("*"*100)
        #     print(spider.headers)
        #     print(spider.cookie)
        return response

    def __del__(self):
        self.driver.close()

