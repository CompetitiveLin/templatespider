# -*- coding:utf-8 -*-
import time
from io import BytesIO, StringIO

import demjson
import requests
from PIL import Image
import json

detection_result_list = list()
whole_zong_img_num = 0
whole_res_img_num = 0
whole_small_img_num = 0
whole_large_img_num = 0
is_one = True
is_preserve = False
detection_num = 0

finish_num = 0


def mustparameter():
    # True 作为必要字段, False 作为非必要字段
    mustp_dict = dict(
        name=True,  # 商品名称
        source=True,  # 来自哪个网站
        cat=True,  # 最后一级目录
        detail_cat=True,  # 详细的目录
        brand=True,  # 品牌
        sales=False,  # 总销量
        total_inventory=False,  # 总货存
        original_price=True,  # 原价
        current_price=True,  # 现价
        about=False,  # 介绍文案
        care=False,  # 保养方式
        description=False,  # 商品功能描述
        url=True,  # 商品链接
        video=False,  # 商品视频
        original_url=False,  # 原始商品链接
        measurements=True,  # 规格尺寸(list)
        attributes=False,  # 商品属性材质列表（list）
        images=False,  # 商品图片(list)

        id=True,
        is_deleted=True,
        created=True,
        updated=True,
        lastCrawlTime=True,
        currency=False,
        # sku_list(SkuItem)SkuItem's list
        sku_list=dict(
            # SkuAttributesItem
            inventory=False,  # 货存
            original_price=True,  # 原价
            current_price=True,  # 现价
            imgs=False,  # 图片
            sku=False,
            url=False,
            attributes=dict(
                colour_img=False,  # 颜色的图片
                colour=False,  # 颜色
                size=False,  # 尺码
                other=False,  # 其他可选择的地方，如沙发是否可折叠啊
            )
        ),
    )
    return mustp_dict


def getstrlength(text):
    return len(str(text))


def set_detection_num_value(num):
    global detection_num
    detection_num = num


field_type_list = ['attributes', 'measurements', 'images', 'imgs','sku_list']
field_type_int = ['is_deleted','total_inventory', 'inventory', 'sales','created','updated']
field_type_dic = ['other', 'attributes']


def check_str(field_value):
    filter_list = [
        u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000', u'\u200a',
        u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
        u'\u200A', u'\u202F', u'\u205F',
        '\t', '\n', '\r', '\f', '\v',
        '<', '>'
    ]
    return all(c not in field_value for c in filter_list)
def check_space(my_detection, field, field_value,sku):
    if sku:
        sku_text = 'sku.'
    else:
        sku_text = ''
    if '   ' in field_value:
        my_detection.append('【' + sku_text + str(field) + '】中存在大量连续空格！T.T')

def check_each_element_len(my_detection, field, field_value,sku):
    if sku:
        sku_text = 'sku.'
    else:
        sku_text = ''
    field_value_list = field_value.split(' ')
    for each_element in field_value_list:
        if each_element and len(each_element) >= 18 : # and '-' not in each_element and '/' not in each_element:
            my_detection.append('【' + sku_text + str(field)  + '】中存在过长的单个字符串！请注意检查T.T')

def check_field_value_tpye(my_detection, field, field_value, sku):
    '''
        检测字段的类型是否正确
    :param my_detection:
    :param field:
    :param field_value:
    :param sku: bool 是否是sku内部字段
    :return:
    '''
    if sku:
        sku_text = 'sku.'
    else:
        sku_text = ''
    if field in field_type_list:
        if not isinstance(field_value, list):
            my_detection.append('【' + sku_text+str(field) + '】字段类型不是list！T.T')
        else:
            if field != 'sku_list':
                for each_value in field_value:
                    if not isinstance(each_value, str):
                        my_detection.append('【' + sku_text+str(field) + '】字段中元素类型不是str！T.T')
                    else:
                        if field == 'attributes':
                            check_space(my_detection, field, each_value, sku)
                            check_each_element_len(my_detection, field, each_value, sku)
                        if not check_str(each_value):
                            my_detection.append('【' + sku_text+str(field) + '】字段中元素含有脏字符！T.T')

    elif field in field_type_int:
        if not isinstance(field_value, int):
            my_detection.append('【' + sku_text+str(field) + '】字段类型不是int！T.T')
    elif field in field_type_dic:
        if not isinstance(field_value, dict):
            my_detection.append('【' + sku_text+str(field) + '】字段类型不是dict！T.T')
    else:
        if not isinstance(field_value, str):
            my_detection.append('【' + sku_text+str(field) + '】字段类型不是str！T.T')
        else:
            if field == 'description' or field == 'about' or field == 'care':
                check_space(my_detection, field, field_value, sku)
                check_each_element_len(my_detection, field, field_value, sku)
            if not check_str(field_value):
                my_detection.append('【' + sku_text+str(field) + '】字段中含有脏字符！T.T')



def check_price(my_detection, field, price_value, sku):
    '''
    检测价格格式是不是数字类型的
    :param my_detection:
    :param field:
    :param price_value:
    :return:
    '''
    if sku:
        sku_text = 'sku.'
    else:
        sku_text = ''
    try:
        price_value_to_float = float(price_value)
    except:
        my_detection.append('【'+ sku_text + str(field) + ': ' + str(price_value) + '】字段格式不对！T.T')


def check_duplicate_imgs(my_detection, field, img_list):
    if img_list:
        raw_lower = list(map(lambda x: x.lower(), img_list))
        if all(image.startswith('http') for image in raw_lower):
            pass
        else:
            my_detection.append(f'【{field}】 图片URL格式不对')

        if len(raw_lower) != len(set(raw_lower)):
            my_detection.append(f'【{field}】存在重复图片T.T, 请重新抓取')


def check_blank_space(my_detection, field, field_value):
    '''
    检测字段内容的空格问题 需要判断的字段有 name, brand, cat, detail_cat

    :param field:
    :param field_value:
    :return:
    '''
    if field_value and len(field_value) > 15 and ' ' not in field_value and '-' not in field_value:
        my_detection.append(f'【{field}:{field_value}】没有空格,请判断是否把字段内容中的空格清洗掉,未清洗掉请跳过T.T')



def check_img_size(my_detection, items, mustparam_k, whole_zong_img_num, whole_small_img_num, whole_large_img_num,
                   whole_res_img_num):
    images = items.get(mustparam_k)
    zong_img_num = 0
    res_img_num = 0
    small_img_num = 0
    large_img_num = 0
    for image in images:
        zong_img_num += 1
        whole_zong_img_num += 1
        if str(image).strip() == '':
            my_detection.append('【' + str(mustparam_k) + '】字段的列表中存在空值！')
            break
        if 'http' not in str(image).strip():
            my_detection.append('【' + str(mustparam_k) + '】字段列表中没有【http】或者【https】标志字符！')
            break
        try:
            img_res = requests.get(image)
            if img_res.status_code == 200:
                try:
                    f = BytesIO(img_res.content)
                    img = Image.open(f)
                    # if img.format != 'JPEG':
                    #     my_detection.append('【' + str(mustparam_k) + '】字段列表中图片格式为【' + str(
                    #         img.format) + '】！')
                    if img.size[0] < 300 and img.size[1] < 300:
                        my_detection.append('【' + str(mustparam_k) + '】字段列表中图片小于300x300！')
                        small_img_num += 1
                        whole_small_img_num += 1
                    else:
                        large_img_num += 1
                        whole_large_img_num += 1
                except Exception as e:
                    my_detection.append('【' + str(mustparam_k) + '】字段存在其他问题：' + str(e))
            else:
                res_img_num += 1
                whole_res_img_num += 1
                my_detection.append('【' + str(mustparam_k) + '】字段列表中图片无法请求，请检查！')
        except:
            my_detection.append('图片请求有错，图片链接为：' + str(image))
    if small_img_num > 0:
        my_detection.append('【sku_list.' + str(mustparam_k) + '】字段列表中图片共' + str(
            zong_img_num) + '张，小图' + str(small_img_num) + '张，请检查！')
    if res_img_num > 0:
        my_detection.append('【sku_list.' + str(mustparam_k) + '】字段列表中图片共' + str(
            zong_img_num) + '张，无法请求图片' + str(res_img_num) + '张，请检查！')


def check_img_size_False(my_detection, items, mustparam_k, sku):
    result = True
    images = items.get(mustparam_k)
    if sku:
        sku_text = 'sku.'
    else:
        sku_text = ''
    if images:
        my_detection.append("【" +sku_text+ str(mustparam_k) + "】只检查第一张图片")
        check_field_value_tpye(my_detection, mustparam_k, images, sku)
        if str(images[0]).strip() == '':
            my_detection.append('【' +sku_text+ str(mustparam_k) + '】字段的列表中存在空值！')
            result = False
        if 'http' not in str(images[0]).strip():
            my_detection.append('【' + sku_text+str(mustparam_k) + '】字段列表中没有【http】或者【https】标志字符！')
            result = False
        try:
            img_res = requests.get(images[0], timeout=20)
            if img_res.status_code == 200:
                try:
                    f = BytesIO(img_res.content)
                    img = Image.open(f)
                    # if img.format != 'JPEG':
                    #     my_detection.append(
                    #         '【' + str(mustparam_k) + '】字段列表中图片格式为【' + str(img.format) + '】！')
                    if img.size[0] < 300 and img.size[1] < 300:
                        my_detection.append('【' + sku_text+str(mustparam_k) + '】字段列表中图片小于300x300！')
                except Exception as e:
                    my_detection.append('【' +sku_text+ str(mustparam_k) + '】字段存在其他问题：' + str(e))
            else:
                my_detection.append('【' +sku_text+ str(mustparam_k)+':'+str(images[0]) + '】字段列表中图片无法请求，请检查！')
        except:
            my_detection.append('图片请求有错，图片链接为：' + str(images[0]))
    # else:
    #     my_detection.append('【' + sku_text + str(mustparam_k) + '】没有抓取到图片，请检查！')
    return result


def scriptdetection(items, skulist=True, skulist_attributes=True):
    global detection_result_list
    global whole_zong_img_num
    global whole_res_img_num
    global whole_small_img_num
    global whole_large_img_num
    my_detection = []
    cat_num = 0
    datail_cat_num = 0
    detection_result_dict = {}
    for mustparam_k, mustparam_v in mustparameter().items():
        url = items.get('url')

        if url:
            detection_result_dict['url'] = url
        else:
            detection_result_dict['url'] = '未知'

        ori_price = items.get('original_price')
        cur_price = items.get('current_price')
        if ori_price and cur_price:
            if float(ori_price) < float(cur_price):
                my_detection.append('【price】现价大于原价, 价格有问题! 请注意T.T')

        if mustparam_k == 'sku_list':
            ### sku 是否检测 ###
            if skulist:
                if 'sku_list' in items and items['sku_list']:
                    for sku in items['sku_list']:
                        for sku_field, sku_validation in sku.items():
                            if sku_validation:
                                if sku_field != 'attributes':
                                    check_field_value_tpye(my_detection, sku_field, sku_validation, sku=True)
                                else:
                                    ori_price = sku_validation.get('original_price')
                                    cur_price = sku_validation.get('current_price')
                                    if ori_price and cur_price:
                                        if float(ori_price) < float(cur_price):
                                            my_detection.append('【sku.price】现价大于原价, 价格有问题! 请注意T.T')

                                if sku_field == 'original_price' or sku_field == 'current_price':
                                    check_price(my_detection, sku_field, sku_validation,sku=True)
                                elif sku_field == 'imgs':
                                    check_duplicate_imgs(my_detection, sku_field, sku_validation)
                                    if mustparam_v[sku_field]:
                                        check_img_size(my_detection, items, sku_field, whole_zong_img_num,
                                                       whole_small_img_num, whole_large_img_num, whole_res_img_num)
                                    else:
                                        if not check_img_size_False(my_detection, items, sku_field,sku=True):
                                            break
                            else:
                                if sku_field == 'imgs':
                                    my_detection.append('【sku_list.' + str(sku_field) + '】重要字段未抓取到！请检查T.T')
                                if mustparam_v[sku_field]:
                                    my_detection.append('【sku_list.' + str(sku_field) + '】重要字段未抓取到！请检查T.T')
                        attributes_ = sku.get('attributes')
                        if attributes_:
                            check_exist = False
                            for field, validation in attributes_.items():
                                if validation:
                                    check_field_value_tpye(my_detection, field, validation,sku=True)
                                    if field == 'colour_img':
                                        if 'http' not in validation:
                                            my_detection.append(
                                                '【sku_list.attributes.' + str(field) + '】字段列表中没有【http】或者【https】标志字符！')
                                    else:
                                        check_exist = True
                                else:
                                    if mustparam_v['attributes'][field]:
                                        my_detection.append('【sku_list.attributes' + str(field) + '】必要字段不存在！请检查T.T')
                            if not check_exist:
                                my_detection.append('【sku_list.attributes】字段中的内容都不存在！请检查T.T')

                        else:
                            my_detection.append("【sku_list.attributes】字段为空, 请去网站检查T.T")
                elif 'sku_list' in items and not items['sku_list']:
                    my_detection.append("【sku_list】字段为空, 请去网站检查T.T")
                elif 'sku_list' not in items:
                    my_detection.append("【sku_list】字段不存在, 打回T.T")
            else:
                my_detection.append("【sku_list】重要字段不做检查")
        else:
            if mustparam_v:
                parameter = items.get(mustparam_k)
                if parameter or parameter == 0:
                    check_field_value_tpye(my_detection, mustparam_k, parameter,sku=False)
                    if mustparam_k == 'name' or mustparam_k == 'source' or mustparam_k == 'brand':
                        check_blank_space(my_detection, mustparam_k, parameter)
                        param_len = getstrlength(items.get(mustparam_k))
                        if param_len > 100:
                            my_detection.append('【' + str(mustparam_k) + '】字段长度太长，请检查是否正确，正确请忽略！')
                    elif mustparam_k == 'original_price' or mustparam_k == 'current_price':
                        check_price(my_detection, mustparam_k, parameter,sku=False)
                    elif mustparam_k == 'cat' or mustparam_k == 'detail_cat':
                        if mustparam_k == 'cat':
                            check_blank_space(my_detection, mustparam_k, parameter)
                            param_len = getstrlength(items.get(mustparam_k))
                            if param_len > 100:
                                my_detection.append('【' + str(mustparam_k) + '】字段长度太长，请检查是否正确，正确请忽略！')
                            cat_num = 1

                        if mustparam_k == 'detail_cat':
                            field_value_list = parameter.split('/')
                            for v in field_value_list:
                                check_blank_space(my_detection, mustparam_k, v)

                            param_len = getstrlength(items.get(mustparam_k))
                            if param_len < 5:
                                my_detection.append('【' + str(mustparam_k) + '】字段长度太短，请检查是否正确，正确请忽略！')
                            datail_cat_num = 1

                        if cat_num == 1 and datail_cat_num == 1:
                            cat = items.get('cat')
                            detail_cat = items.get('detail_cat')
                            if '/' in detail_cat:
                                if cat in detail_cat:
                                    detail_cat = detail_cat.replace(cat, '').strip()[-1:]
                                    if detail_cat != '/':
                                        my_detection.append('【detail_cat】字段中存在无用字符，请检查是否正确！')
                                else:
                                    my_detection.append('【detail_cat】字段中找不到【cat】字段，请检查是否正确！')
                            else:
                                if cat == detail_cat:
                                    my_detection.append('【cat】与【detail_cat】相同，请检查是否正确，正确请忽略！')
                                else:
                                    my_detection.append('【detail_cat】字段没有使用【/】分割，请检查是否正确！')
                    elif mustparam_k == 'url':
                        if 'http' not in items.get(mustparam_k):
                            my_detection.append('【' + str(mustparam_k) + '】字段中没有【http】或者【https】标志字符！')
                    elif mustparam_k == 'images':
                        check_duplicate_imgs(my_detection,mustparam_k, items.get(mustparam_k))
                        check_img_size(my_detection, items, mustparam_k, whole_zong_img_num, whole_small_img_num,
                                       whole_large_img_num, whole_res_img_num)
                    elif mustparam_k == 'is_deleted':
                        if parameter != 0:
                            my_detection.append(f' 【{mustparam_k}】重要字段不正确, 返回脚本查看T.T')
                else:
                    my_detection.append('【' + str(mustparam_k) + '】重要字段不存在！请注意检查,原网站是否含有该字段内容~~~~~~~~~~')
            else:
                if mustparam_k == 'images':
                    check_duplicate_imgs(my_detection, mustparam_k, items.get(mustparam_k))
                    if not check_img_size_False(my_detection, items, mustparam_k,sku=False):
                        break
                parameter = items.get(mustparam_k, f'not exist this {mustparam_k}')
                if parameter and parameter != f'not exist this {mustparam_k}':
                    check_field_value_tpye(my_detection, mustparam_k, parameter,sku=False)
                    # 检测非必要字段内容
                    if parameter == 'None' or parameter == 'none':
                        my_detection.append("【" + str(mustparam_k) + "】字段内容是字符串的None, 不正确!!!!")
                # 可以判断非必要字段的抓取情况
                # elif parameter and parameter == f'not exist this {mustparam_k}':
                #     my_detection.append("【" + str(mustparam_k) + "】非必要字段未抓取!")
                elif not parameter:
                    my_detection.append("【" + str(mustparam_k) + "】字段内容是空!, 请检查!T.T")

    detection_result_dict['detection_infos'] = list(set(my_detection))
    detection_result_dict['items'] = items

    detection_result_list.append(detection_result_dict)
    global finish_num
    finish_num += 1
    print("第" + str(finish_num) + "个检测完成。")
    global detection_num
    detection_num -= 1
####################################
    # print(list(set(my_detection)))


def detection_main(items, website, num, skulist=True, skulist_attributes=True):
    # items:解析信息
    # website：站点名称
    # num:检测个数
    # skulist:是否对sku检测,默认检测
    # skulist_attributes:是否对sku.attributes检测,默认检测
    global is_one
    global is_preserve
    global detection_num
    if is_one:
        print("提示：正在进入检测，共准备检测【" + str(
            num) + "】个，检测图片字段时，会发送关于每张图片的请求，时间较长，可自行调整检测个数；若请求超时或请求错误，请检查图片的正确性，如果图片无误，可自行关闭图片字段检测。")
        detection_num = num
        is_one = False
    print("=" * 50)
    scriptdetection(items, skulist, skulist_attributes)
    if detection_num <= 0:
        if is_preserve == False:
            is_preserve = True
            t = int(time.time() * 1000)
            with open(website + "_" + str(t) + ".txt", "a+", encoding="utf-8") as file:
                file.write(json.dumps(json.loads(demjson.encode(detection_result_list)), ensure_ascii=False))
            print("【检测文件】保存完毕！")

