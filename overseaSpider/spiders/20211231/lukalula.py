# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'lukalula'


class lukalulaSpider(scrapy.Spider):
    name = website
    start_urls = ['https://www.lukalula.com/']

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
        super(lukalulaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "若白")

    is_debug = True
    custom_debug_settings = {
        # 'CLOSESPIDER_ITEMCOUNT':5,
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 8,
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

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
        for pattern in label_pattern:
            labels = re.findall(pattern, text, re.S)
            for label in labels:
                text = text.replace(label, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        # print('text',text)
        return text

    def filter_text(self, input_text):
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls1 = ['https://www.lukalula.com/new-in/',
                          'https://www.lukalula.com/hot-sale/',
                          'https://www.lukalula.com/collections/casual-everyday-dresses-5123/',
                          'https://www.lukalula.com/collections/midi-maxi-dresses-5182/',
                          'https://www.lukalula.com/collections/floral-dress-31924/',
                          'https://www.lukalula.com/collections/mini-dress-42293/',
                          'https://www.lukalula.com/collections/long-sleeve-dresses-54053/',
                          'https://www.lukalula.com/activity/maternity-lace-tulle-dress-3388/',
                          'https://www.lukalula.com/activity/maternity-striped-maxi-dress-9010/',
                          'https://www.lukalula.com/activity/bodycon-dress-8966/',
                          'https://www.lukalula.com/activity/v-neck-dress-8968/',
                          'https://www.lukalula.com/activity/bohemian-11192/',
                          'https://www.lukalula.com/activity/backless-dress-11249/',
                          'https://www.lukalula.com/collections/photograph-dress-44755/',
                          'https://www.lukalula.com/collections/long-sleeve-t-shirts-54878/',
                          'https://www.lukalula.com/collections/short-sleeve-t-shirts-54900/',
                          'https://www.lukalula.com/collections/hoodies-46833/',
                          'https://www.lukalula.com/collections/sweaters-46839/',
                          'https://www.lukalula.com/collections/outerwears-54879/',
                          'https://www.lukalula.com/collections/jumpsuits-45336/',
                          'https://www.lukalula.com/collections/trousers-58369/',
                          'https://www.lukalula.com/collections/shorts-67187/',
                          'https://www.lukalula.com/collections/kids-72027/',
                          'https://www.lukalula.com/collections/matching-72028/',
                          'https://www.lukalula.com/collections/maternity-72026/',
                          'https://www.lukalula.com/collections/underwear-58291/',
                          'https://www.lukalula.com/collections/matching-46042/',
                          'https://www.lukalula.com/collections/baby-0-2y-58936/',
                          'https://www.lukalula.com/collections/kids-48258/',
                          'https://www.lukalula.com/clearance/'
                          ]
        # category_urls1=response.xpath('//ul[@class="site-nav"]'
        #                               '//div[@class="bolder"]/a/@href').getall()
        # print(category_urls1)
        for category_url in category_urls1:
            if "http" not in category_url:
                tur='https://www.lukalula.com'+category_url
            else:
                tur=category_url

            yield scrapy.Request(
                url=tur,
                callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath('//a[@class="product-box-a"]/@href').getall()
        # print(detail_url_list)
        if len(detail_url_list) == 0:
            return
        for detail_url in detail_url_list:
            if "http" not in detail_url:
                tur='https://www.lukalula.com'+detail_url
            else:
                tur=detail_url
            yield scrapy.Request(
                url=tur,
                # url="https://www.lukalula.com/products/maternity-sexy-boat-neck-pure-color-dress-1448619.html?from=collections",
                # url="https://www.slumberland.com/p/collage-rocker-recliner/La-Z-BoyCollageRockerRecliner.html?dwvar_La-Z-BoyCollageRockerRecliner_La-Z-BoyCollageColors=Coffee&cgid=chairs-all%20chairs#start=1",
                # url="https://www.lukalula.com/products/maternity-solid-v-neck-lace-up-long-sleeve-dress-3930043.html?from=collections&variant=56300749",
                callback=self.parse_detail,

            )
        if "?pageNo" not in response.url:
            next_page_url = response.url + "?pageNo=2"
        else:
            response_url = response.url
            split_str = '='
            base_url = "=".join(response_url.split(split_str)[0:len(response_url.split(split_str)) - 1])
            page_num = int(response_url.split(split_str)[-1]) + 1
            next_page_url = base_url + split_str + str(page_num)
            # print("nextpae", next_page_url)
        # print("下一下",next_page_url)
        if next_page_url:
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        IMinfo = response.xpath('//script[@type="text/javascript"]/text()').getall()
        IMinfoJSONall = self.filter_text(self.filter_html_label(''.join(IMinfo)))
        prinfojson = re.search('var productJson = (.*?);var goodsDetail', IMinfoJSONall, re.S)
        prinfo=json.loads(prinfojson.group(1))
        bd = "".join(re.findall('"brand": (.*?)\},', IMinfoJSONall, re.S))
        # bd = response.xpath('//span[@itemprop="brand"]/a/text()').get()
        if bd:
            items['brand'] = re.search('"name": "(.*?)"', bd.group(1)).group(1) \
                .replace('\n', '').replace('&', '').replace('\xa0', '').replace('(', '')
        else:
            items['brand'] = ''
        items['name'] = prinfo['title'].replace('\n', '').replace('\t', '').replace('&', '')
        current_price = prinfo['price']
        if current_price.strip()=='':
            current_price=\
                self.filter_text(self.filter_html_label(''.join(response.xpath(
            '//div[@class="product-price"]/span/text()').getall())))
        # print(current_pricel)
        if not current_price:
            current_price = response.xpath(
                '//div[@class="product-price"]/span/text()').get()
            if not current_price:
                current_price = response.xpath('//div[@class="selected-color-price prix"]/text()').get()
                if not current_price:
                    current_price = response.xpath(
                        '//div[@class="current-price"]//span[@itemprop="price"]/@content').get()
        try:
            isthereoriginal_price =prinfo['market_price']
        except:
            isthereoriginal_price=None

            # print(isthereoriginal_price)
        # print(isthereoriginal_price)
        if isthereoriginal_price:
            # original_price = response.xpath("//span[@data-price-type='oldPrice']/span[@class='price']/text()").getall()[0]
            items["original_price"] = isthereoriginal_price.strip()
            # print("原价", original_price)
        else:
            items["original_price"] = current_price.replace('€', "").strip()
        items["current_price"] =  current_price.replace('€', "").strip()
        da = response.xpath('//div[@class="breadcrumb"]/a/text()').getall()
        # print(da)

        items["detail_cat"] = self.filter_text(self.filter_html_label('/'.join(da[:])))
        # items["cat"] = response.xpath('//div[@class="product-item__description"]/div[@class="product-item__category"]/text()').get()
        items["cat"] = da[-1]
        about = response.xpath('//div[@class="breadcrumb"]/a/text()').getall()
        if about:
            items["about"] = self.filter_text(self.filter_html_label(''.join(about))).replace('\r', '').replace('\n',
                                                                                                                '')
        else:
            items["about"] = ''
        items["source"] = website
        de = response.xpath('//div[@class="accord-cont description-html"]//text()').getall()
        # de2 = response.xpath('//div[@id="tab-description"]/p/ul/li/text()').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(de)))

        # IMinfo = response.xpath('//script[@type="text/x-magento-init"]/text()').getall()
        # IMinfoJSONall = self.filter_text(self.filter_html_label(''.join(IMinfo)))
        # print('SSS', IMinfoJSONall)

        items["images"] = []
        imgs = response.xpath('//div[@class="pdp-featured js-pdp-featured"]//img/@src'
                              ).getall()
        # print("ss",imgs)

        for i in list(imgs):

            items['images'].append(i.strip())
            # R = "".join(k[:len(k) - 1])
            # if "png" in R:
            #     R2="-".join(R.strip().split("-")[:len(R.strip().split("-"))-1])+'-500x500.png'
            #     items['images'].append(R2)
            # else:
            #     items['images'].append(R.strip())
        if not items['images']:
            imgs = response.xpath('//meta[@property="og:image"]/@content'
                                  ).get()
            items['images'].append(imgs)

            # items['images'].append(u+'sw=500&sfrm=jpeg&q=70')
        items["sku_list"] = []
        variants=prinfo["variants"]
        colorim=prinfo["colorImages"]
        opp=prinfo['options']
        if variants:
            if len(opp)==2:
                for i in variants:
                    skuitem = SkuItem()
                    skuatt = SkuAttributesItem()
                    skuatt['size'] =i["attrLang"]["size"]
                    skuatt['colour']=i["attrLang"]["color"]
                    skuatt['colour_img']=colorim[skuatt['colour']]
                    skuitem["attributes"] = skuatt
                    try:
                        skuitem['imgs']=[skuatt['colour_img'].split("!")[0]+"!w600-h600"]
                    except:
                        pass

                    skuitem["current_price"] =str(i["price"])
                    skuitem["original_price"] = str(i["market_price"])
                    if skuitem["original_price"].strip()=="":
                        skuitem["original_price"]=skuitem["current_price"]

                    items["sku_list"].append(skuitem)
            if  len(opp)==1:
                for i in variants:
                    skuitem = SkuItem()
                    skuatt = SkuAttributesItem()
                    if opp[-1]=="Color":
                        skuatt['colour'] = i["attrLang"]["color"]
                        skuatt['colour_img'] = colorim[skuatt['colour']]
                    elif opp[-1]=="Size":
                        skuatt['size'] = i["attrLang"]["size"]
                    else:
                        skuatt['other'] = {opp[-1]:i["attrLang"][opp[-1].lower()]}
                    try:
                        skuitem['imgs'] = [skuatt['colour_img'].split("!")[0] + "!w600-h600"]
                    except:
                        pass
                    skuitem["attributes"] = skuatt
                    skuitem["current_price"] = "$"+str(i["price"])
                    skuitem["original_price"] = "$"+str(i["price"])
                    items["sku_list"].append(skuitem)

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

        # detection_main(items=items,
        #                website=website,
        #                num=self.settings['CLOSESPIDER_ITEMCOUNT'],
        #                skulist=True,
        #                skulist_attributes=True)
        print(items)
        # yield items







