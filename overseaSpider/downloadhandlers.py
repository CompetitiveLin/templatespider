# -*- coding: utf-8 -*-

import httpx
from typing import Optional
import random
import ssl

# ssl._create_default_https_context = ssl._create_unverified_context

from twisted.internet.defer import Deferred

from scrapy import signals
from scrapy.http import Request, Response, Headers, HtmlResponse
from scrapy.spiders import Spider
from scrapy.settings import Settings
from scrapy.crawler import Crawler
from scrapy.utils.defer import deferred_from_coro, deferred_f_from_coro_f
from scrapy.responsetypes import responsetypes
from scrapy.core.downloader.handlers.http import HTTPDownloadHandler

import aiohttp

ORIGIN_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
                  'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES')


class HttpxDownloadHandler(HTTPDownloadHandler):
    def __init__(self, settings: Settings, crawler: Optional[Crawler] = None):
        super().__init__(settings, crawler)
        self.client = None
        crawler.signals.connect(self._engine_started, signals.engine_started)

    @deferred_f_from_coro_f
    async def _engine_started(self, signal, sender):
        client = httpx.AsyncClient(http2=True)
        self.client = await client.__aenter__()

    def download_request(self, request: Request, spider: Spider) -> Deferred:
        if request.meta.get("h2"):
            return deferred_from_coro(self._download_request(request, spider))

        return super().download_request(request, spider)  # 普通下载

    async def _download_request(self, request: Request, spider: Spider) -> Response:
        """httpx下载逻辑"""
        response = await self.client.request(request.method,
                                             request.url,
                                             content=request.body,
                                             headers=request.headers.to_unicode_dict(),
                                             cookies=request.cookies)

        headers = Headers(response.headers)
        if "Content-Encoding" in headers and b"gzip" in headers["Content-Encoding"]:
            headers["Content-Encoding"] = b'utf-8'

        headers["Content-Encoding"] = b'utf-8'
        respcls = responsetypes.from_args(headers=headers,
                                          url=str(response.url),
                                          body=response.content)
        return respcls(url=str(response.url),
                       status=response.status_code,
                       headers=headers,
                       body=response.content,
                       flags=["httpx"],
                       request=request,
                       protocol=response.http_version)
        # return HtmlResponse(url=str(response.url), headers=headers, body=response.content, encoding='utf-8')

    @deferred_f_from_coro_f
    async def close(self):
        await self.client.__aexit__()
        await super().close()


class SSLFactory:
    def __init__(self):
        self.ciphers = ORIGIN_CIPHERS.split(":")

    def __call__(self) -> ssl.SSLContext:
        random.shuffle(self.ciphers)
        ciphers = ":".join(self.ciphers)
        ciphers = ciphers + ":!aNULL:!eNULL:!MD5"

        context = ssl.create_default_context()
        context.set_ciphers(ciphers)
        return context


sslgen = SSLFactory()


class Ja3DownloadHandler(HTTPDownloadHandler):
    def __init__(self, settings: Settings, crawler: Optional[Crawler] = None):
        super().__init__(settings, crawler)
        self.client = None
        crawler.signals.connect(self._engine_started, signals.engine_started)

    @deferred_f_from_coro_f
    async def _engine_started(self, signal, sender):
        client = aiohttp.ClientSession()
        self.client = await client.__aenter__()

    def download_request(self, request: Request, spider: Spider) -> Deferred:
        if request.meta.get("ja3"):
            return deferred_from_coro(self._download_request(request, spider))
        return super().download_request(request, spider)  # 普通下载

    async def _download_request(self, request: Request, spider: Spider) -> Response:
        """aiohttp下载逻辑"""
        async with self.client.request(request.method,
                                       request.url,
                                       data=request.body,
                                       headers=request.headers.to_unicode_dict(),
                                       cookies=request.cookies,
                                       ssl=sslgen()) as response:
            headers = Headers(response.headers)
            if "Content-Encoding" in headers and b"gzip" in headers["Content-Encoding"]:
                headers["Content-Encoding"] = b'utf-8'

            headers["Content-Encoding"] = b'utf-8'
            body = await response.read()
            respcls = responsetypes.from_args(headers=headers,
                                              url=str(response.url),
                                              body=body)

            return respcls(url=str(response.url),
                           status=response.status,
                           headers=headers,
                           body=body,
                           flags=["ja3"],
                           request=request,
                           protocol=response.version)

    @deferred_f_from_coro_f
    async def close(self):
        await self.client.__aexit__(None, None, None)
        await super().close()
