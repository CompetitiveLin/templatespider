# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'art'

class ArtSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['art.com']
    # start_urls = ['http://art.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(ArtSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "凯棋")
        self.headers = {
          'authority': 'www.art.com',
          'pragma': 'no-cache',
          'cache-control': 'no-cache',
          'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"macOS"',
          'dnt': '1',
          'upgrade-insecure-requests': '1',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
          'sec-fetch-site': 'none',
          'sec-fetch-mode': 'navigate',
          'sec-fetch-user': '?1',
          'sec-fetch-dest': 'document',
          'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
          'cookie': 'ipCountryCode=HK; sessionid=F479FA53F39044BFBA6906616434537C; PID=5377eb565b9144079447a69989637446; CID=F479FA53F39044BFBA6906616434537C; CustSessionID=F479FA53F39044BFBA6906616434537C; IPCountry=HK; CountryCode=HK; CurrentCurrencyCode=USD; apt=8f42e4f83450413e80c5f0b4e1adcd91; CustomerZoneID=3; AKAI=0:1632277664; optimizelyEndUserId=oeu1632277664418r0.17232334069339572; elb=1; _ga=GA1.2.1753771112.1632277666; _gid=GA1.2.1256200117.1632277666; _gcl_au=1.1.519938701.1632277666; UTE=VisitId=bc5230a99a5861f5; UTEPixelId=0; ASP.NET_SessionId=haty20obhb12ryj23xw152vi; _csTraffic=%7B%22adID%22%3A%22%22%2C%22source%22%3A%2220.81.114.208%3A8000%22%2C%22campaign%22%3A%22%28referral%29%22%2C%22medium%22%3A%22referral%22%2C%22term%22%3A%22%22%2C%22content%22%3A%22/%22%7D; _fbp=fb.1.1632277666297.343545497; _pin_unauth=dWlkPU5qWmlNMll6WkdZdE5EVTFZaTAwTWpVMUxUaGlaVFV0WmpnMU5tWmpaRGt5TWpSaA; __attentive_id=6388e467cd1f47969d18640dc67a5849; __attentive_cco=1632277670386; __attentive_ss_referrer="http://20.81.114.208:8000/"; __attentive_dv=1; intercom-id-yk60jooh=4cdad98b-19b2-4e36-8fa7-fb10287a2cdb; intercom-session-yk60jooh=; apcredirected=true; _csSessionID=1958095468.1632281292; sg=true; testab={"fad":true}; SCID=0=1&1=8&2=2&3=2; getItByDate=; _gat=1; ap=wtVisit=1&langIso=en&accounttype=1&env=&islangdefault=true&profileURL=%2Fme%2FgYoN5wY5by1ig5jTKGq4GA2%2F&accountid=8012947283; _uetsid=ac1056801b4c11eca17c4f9fc42f33e9; _uetvid=ac109e901b4c11ec8a87f94604d680d9; stc121333=env:1632281292%7C20211023032812%7C20210922040047%7C5%7C1108612:20220922033047|uid:1632277666216.2062809752.2882223.121333.1765377358:20220922033047|srchist:1108613%3A1%3A20211023022746%7C1108612%3A1632281292%3A20211023032812:20220922033047|tsa:1632281292109.1659435713.5032492.848120484805398.9:20210922040047; __kla_id=eyIkcmVmZXJyZXIiOnsidHMiOjE2MzIyNzc2NjcsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly93d3cuYXJ0LmNvbS8ifSwiJGxhc3RfcmVmZXJyZXIiOnsidHMiOjE2MzIyODE0NDcsInZhbHVlIjoiaHR0cHM6Ly93d3cuYXJ0LmNvbS8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly93d3cuYXJ0LmNvbS9zaG9wL2FydC1zdWJqZWN0cy8ifX0=; arts=stp=true&lastPage=https://www.art.com/gallery/id--b1822/abstract-posters.htm&sourcereferrer=https://www.art.com/gallery/id--b1822/abstract-posters.htm&startreferrer=https://www.art.com/gallery/id--b1822/abstract-posters.htm&EnviromentLoaded=true&ac=true&bnr=1; __attentive_pv=6; ipCountryCode=HK; CustSessionID=F479FA53F39044BFBA6906616434537C; ap=wtVisit=1&langIso=en&accounttype=1&env=&islangdefault=true&profileURL=%2Fme%2FgYoN5wY5by1ig5jTKGq4GA2%2F&accountid=8012947283; sessionid=F479FA53F39044BFBA6906616434537C'
        }

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
        'HTTPERROR_ALLOWED_CODES': [302]
    }

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'<div class="cbb-frequently-bought-container cbb-desktop-view".*?</div>', r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
        for pattern in label_pattern:
            labels = re.findall(pattern, text, re.S)
            for label in labels:
                text = text.replace(label, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

    def start_requests(self):
        url_list = [
            "https://www.art.com/shop/art-subjects/"
        ]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                dont_filter=True
            )

    def parse(self, response):
        url_list = response.xpath("//ul[@class='shop-nav']/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list[:1]:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers

            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//div[@class='grid-container scroll-column']/div/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )


        # next_page_url = response.xpath("//a[@class='pagination-caret-container caret-right']/@href").get()
        # if next_page_url:
        #    next_page_url = response.urljoin(next_page_url)
        #    print("下一页:"+next_page_url)
        #    yield scrapy.Request(
        #        url=next_page_url,
        #        callback=self.parse_list,
        #    )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        original_price = response.xpath("//div[@class='products-wrapper']/button//div[@class='price']/text()").get()
        current_price = response.xpath("//div[@class='products-wrapper']/button//div[@class='price']/text()").get()
        items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
        items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)

        items["brand"] = response.xpath("//a[@class='artist-title']/text()").get()
        items["name"] = response.xpath('//h1[@itemprop="name"]/text()').get()
        # attributes = list()
        # items["attributes"] = attributes
        description = response.xpath("//div[@class='product-content']//text()").getall()
        items["about"] = "".join(description)
        description = re.findall('"itemDisplayTypeDescription":(.*?)","description"', response.text)[0]
        items["description"] = self.filter_html_label("".join(description))
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        items["source"] = website
        images_list = response.xpath('//div[@class="hero-zoom-wrapper"]/img/@src').getall()
        items["images"] = images_list

        items["cat"] = 'art'
        items["detail_cat"] = 'art'

        size_list = response.xpath('//div[contains(@class,"size-button")]/text()').getall()

        sku_list = list()
        for size in size_list:
            sku_item = SkuItem()
            sku_item["original_price"] = items["original_price"]
            sku_item["current_price"] = items["current_price"]
            attributes = SkuAttributesItem()
            attributes["size"] = size
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
