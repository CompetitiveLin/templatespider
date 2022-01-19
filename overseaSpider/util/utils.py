import sys
import os
import time
import re
import json
import logging
import inspect
import traceback
import functools
import requests
import platform

import tldextract
from urllib.parse import urlparse

from inspect import getcallargs

from logging.handlers import TimedRotatingFileHandler


def get_logger():
    logger = logging.getLogger(__name__)
    this_file = inspect.getfile(inspect.currentframe())
    dirpath = os.path.abspath(os.path.dirname(this_file))

    dir = os.path.join(os.path.dirname(dirpath), "log")
    if not os.path.isdir(dir):
        os.mkdir(dir)

    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-5s %(filename)-10s  %(message)s')
    handler = TimedRotatingFileHandler(os.path.join(dir, "spider.txt"), when="midnight", interval=1, backupCount=20)
    handler.setFormatter(formatter)
    handler.flush()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)



logger = get_logger()


def notify(spider_name, info):
    text = f"「{str(spider_name)}」出错了，相关信息如下「{str(info)}」"
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/3b352dfb-7302-40c2-801b-e3d97557a799"
    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "【FasionSpider Notify ⏰】",
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": text
                            }
                        ]
                    ]
                }
            }
        }
    }
    try:
        requests.post(url, headers={"Content-type": "application/json"}, data=json.dumps(data))
    except Exception as e:
        logging.info(f"Faishu Notify failed! Err: {e}")


def sort_set(set_list, old_list):
    set_list.sort(key=old_list.index)
    return set_list


def isLinux():
    '''
    判断当前运行平台
    '''
    sysstr = platform.system()
    if (sysstr == "Linux"):
        return True
    else:
        # print("Other System ")
        pass
    return False


# 捕获函数异常的装饰器
def catch_error(status=False):
    """
    :param status: 函数发生异常时的返回值，默认False
    :return: status
    """

    def wrapper(func):

        @functools.wraps(func)
        def log(*args, **kwargs):
            # 被装饰的函数名字
            funcname = func.__name__
            try:
                # all_args = getcallargs(func, *args, **kwargs)
                return func(*args, **kwargs)
            except:
                # 记录发生异常的堆栈信息
                error = traceback.format_exc()
                # print("*" * 100)
                print(u"函数{}发生异常:{}".format(funcname, error))

            return status

        return log

    return wrapper




def filter_text(input_text):
    input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
    input_text = re.sub(r'<.*?>', ' ', input_text)
    filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                   u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                   u'\u200A', u'\u202F', u'\u205F']
    for index in filter_list:
        input_text = input_text.replace(index, "").strip()
    return input_text


def list2str(l):
    if isinstance(l, list) and all(isinstance(s, str) for s in l):
        return re.sub(r' +', ' ', re.sub(r'[\r\n\t]', '', ''.join(l))).replace('\xa0', '').strip()


def str_list(l):
    if isinstance(l, list) and all(isinstance(s, str) for s in l):
        return [re.sub(r' +', ' ', re.sub(r'[\r\n\t]', '', s)).replace('\xa0', '').strip() for s in l]


def strip_str(s):
    if isinstance(s, str):
        return re.sub(r' +', ' ', re.sub(r'[\r\n\t]', '', s)).replace('\xa0', '').strip()


def strip_url(url):
    if isinstance(url, str):
        domain = tldextract.extract(url).domain
        suffix = tldextract.extract(url).suffix
        return domain + '.' + suffix


def strip_full_url(url):
    if isinstance(url, str):
        extract = urlparse(url)
        return extract.scheme + '://' + extract.netloc


def strip_domain(url):
    if isinstance(url, str):
        domain = tldextract.extract(url).domain
        return domain


def chunks(lst, n):
    if isinstance(lst, list):
        l = []
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            l.append(lst[i:i + n])
        return l




if __name__ == '__main__':
    @catch_error()
    def test1(arg=None):
        item = {
            "test": "asdasd"
        }
        # print(item)
        yield item


    status = test1()
