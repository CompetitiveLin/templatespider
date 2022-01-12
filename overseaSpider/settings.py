BOT_NAME = 'overseaSpider'

SPIDER_MODULES = ['overseaSpider.spiders']
NEWSPIDER_MODULE = 'overseaSpider.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

DOWNLOADER_MIDDLEWARES = {
    # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 99,
    # 'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
    # 'overseaSpider.middlewares.RuanzhuUpdateCookieMiddleware': 100
}
ITEM_PIPELINES = {
   'overseaSpider.pipelines.OverseaspiderPipeline': 300,
}
MONGODB_DB= 'test'
MONGODB_COLLECTION = 'test_data'  # 存放本次数据的表名称
MONGO_CDN = "cdn"
# USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36"

CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 0
LOG_LEVEL = 'INFO'
# LOG_FILE='local.log'
# LOG_STDOUT=True
COOKIES_ENABLED = True
# COOKIES_DEBUG=True
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 7 * 24 * 3600
# HTTPCACHE_DIR = "/Users/radon/Desktop/mogu/overseaSpider/cache"
HTTPCACHE_IGNORE_HTTP_CODES = [403, 301, 401, 500, 503]
HTTPCACHE_POLICY = "overseaSpider.middlewares.DummyPolicy"
RETRY_ENABLED = False  # 是否开启重试
RETRY_TIMES = 1  # 重试次数
DOWNLOAD_TIMEOUT = 10

COMMANDS_MODULE = "overseaSpider.commands"

TEMPLATES_DIR = r"D:\work\overseaspider\overseaSpider\templates"

import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ASYNCIO_EVENT_LOOP = "asyncio.SelectorEventLoop"

from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

# H2
import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ASYNCIO_EVENT_LOOP = "asyncio.SelectorEventLoop"

from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')