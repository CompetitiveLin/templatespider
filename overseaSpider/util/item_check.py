import logging
import traceback


logger = logging.getLogger(__name__)


def list_is_instance(list_, type_):
    return isinstance(list_, list) and \
           all(isinstance(element, type_) for element in list_)


def check_str(field_value):
    filter_list = [
        u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
        u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
        u'\u200A', u'\u202F', u'\u205F',
        '\t', '\n', '\r', '\f', '\v'
    ]
    return all(c not in field_value for c in filter_list)


def check_space(field, field_value):
    '''

    :param field: 字段名字
    :param field_value: 字段内容
    :return:
    '''
    if '   ' in field_value:
        logger.warning(f"注意: {field}:{field_value} 中存在大量连续空格  \n")


def check_content(type_, field_value, field):
    '''
    :param type_: content 字段类型
    :param field_value: 字段的value
    :param field: 字段的名字
    :return:
    '''
    if type_ in {'int'}:
        if type_ == 'int' and isinstance(field_value, int):
            pass
        else:
            raise Exception(f"{field}: {field_value} 字段类型不对T.T, 请修改~")
    elif type_ == 'str' and isinstance(field_value, str) \
            and check_str(field_value):
        check_space(field, field_value)
        pass
    elif type_ == 'list_str' and list_is_instance(field_value, str) \
            and all(check_str(element) for element in field_value):
        for ele in field_value:
            check_space(field, ele)
        pass
    elif type_ == 'dict' and all(isinstance(element, str) for element in field_value.keys()):
        for k in field_value.items():
            check_space(field, k)
        pass
    else:
        raise Exception(f"item field error! {field}: {field_value}")


def check_blank_space(field,field_value):
    if field_value and len(field_value) > 12 and ' ' not in field_value:
        logger.warning(f'重要字段 {field}: {field_value} 没有空格,请判断是否把字段内容中的空格清洗掉,未清洗掉请跳过')



def check_duplicate_imgs(field ,img_list):
    if img_list:


        raw_lower = list(map(lambda x: x.lower(), img_list))

        if all(image.startswith('http') for image in raw_lower):
            pass
        else:
            raise Exception(f'重要字段 {field}: {img_list} 图片URL格式不对')

        if len(raw_lower) != len(set(raw_lower)):
            raise Exception(f'重要字段 {field}: {img_list} 存在重复图片T.T, 请重新抓取')



def check_fields(dictionary, validations):
    for field, validation in validations.items():
        field_value = dictionary.get(field)
        can_be_None = validation['can_be_None']
        type_ = validation['type']


        if field == 'name':
            check_blank_space(field, field_value)
        if field == 'images':
            check_duplicate_imgs(field, field_value)

        special_field = ['detail_cat', 'cat', 'brand']
        if field in special_field:
            if field == 'detail_cat':
                field_value_list = field_value.split('/')
                for v in field_value_list:
                    check_blank_space(field, v)
            else:
                check_blank_space(field, field_value)
            if field_value == None:
                logger.warning(f"注意: {field} 是NoneType, 如果没有最好提换成'' \n")
            else:
                check_content(type_, field_value, field)



        elif field == 'is_deleted':
            if field_value == 0:
                pass
            else:
                raise Exception(f'重要字段 {field} 不正确, 返回脚本查看~')

        elif can_be_None and not field_value:
            pass

        elif can_be_None and field_value:
            check_content(type_, field_value, field)

        elif not can_be_None:
            if field_value:
                check_content(type_, field_value, field)
            else:
                raise Exception(f'重要字段 {field} 为空T.T, 重新抓取~')


def check_price(price_type: str, price_value: str):
    try:
        price_value_to_float = float(price_value)
    except:
        # logger.warning(f'{price_type}: {price_value} 的格式不对!~ 非数字格式T.T')
        raise Exception(f'{price_type}: {price_value} 的格式不对!~ 非数字格式T.T')


def check_images(images: list):
    return all(image.startswith('http') for image in images)


def check_item(item):
    try:
        check_fields(item, item_validations)
        if item['sku_list'] is None:
            raise Exception('item.sku_list is None!')
        for sku in item['sku_list']:
            check_fields(sku, sku_validations)

            attributes_ = sku['attributes']
            check_fields(attributes_, sku_attr_validations)
            other = attributes_.get('other')
            if 'imgs' in sku and sku.get('imgs'):
                check_duplicate_imgs('sku_imgs', sku.get('imgs'))

            if 'colour' in attributes_ and not attributes_.get('colour'):
                logger.warning(f"注意: sku_colour 为空 \n")
            if 'size' in attributes_ and not attributes_.get('size'):
                logger.warning('注意: sku_size 为空 \n')
            if 'other' in attributes_ and not attributes_.get('other'):
                logger.warning(f"注意: sku_other 为空 \n")

            if attributes_.get('colour') or attributes_.get('size') or \
                    other and all(isinstance(element, str) for element in other.values()):
                pass
            else:
                raise Exception('sku attributes error!')

        cat = item['cat']
        detail_cat = item['detail_cat']
        if (cat and not detail_cat) or (not cat and detail_cat):
            raise Exception('cat 或者 detail_cat 不存在')
        if cat and detail_cat:
            cats = detail_cat.split("/")
            if cat in cats[-1]:
                pass
            else:
                logger.warning(f"注意: cat和detail_cat可能不匹配! 检查一下name或者cat中是否有/ \ncat:{cat}\ndetail_cat:{detail_cat} \n")

        check_price('original_price', item['original_price'])
        check_price('current_price', item['current_price'])
        check_images(item['images'])
        for sku in item['sku_list']:
            check_price('sku_original_price', sku['original_price'])
            check_price('sku_current_price', sku['current_price'])


    except Exception:
        print("-" * 100)
        logger.error(f"error processing item:\n{item}")
        traceback.print_exc()
        print("-" * 100)
        return False

    return True


item_validations = {
    'id': {
        'can_be_None': False,
        'type': 'str'
    },
    'name': {
        'can_be_None': False,
        'type': 'str'
    },
    'source': {
        'can_be_None': False,
        'type': 'str'
    },
    'cat': {
        'can_be_None': False,
        'type': 'str'
    },
    'detail_cat': {
        'can_be_None': False,
        'type': 'str'
    },
    'brand': {
        'can_be_None': False,
        'type': 'str'
    },
    'sales': {
        'can_be_None': True,
        'type': 'int'
    },
    'attributes': {
        'can_be_None': True,
        'type': 'list_str'
    },
    'measurements': {
        'can_be_None': False,
        'type': 'list_str'
    },
    'total_inventory': {
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
    'about': {
        'can_be_None': True,
        'type': 'str'
    },
    'care': {
        'can_be_None': True,
        'type': 'str'
    },
    # 'sku_list': {
    #     'can_be_None': True,
    #     'type': 'list'
    # },
    'images': {
        'can_be_None': False,
        'type': 'list_str'
    },
    'description': {
        'can_be_None': True,
        'type': 'str'
    },
    'url': {
        'can_be_None': False,
        'type': 'str'
    },
    'video': {
        'can_be_None': True,
        'type': 'str'
    },
    'is_deleted': {
        'can_be_None': False,
        'type': 'int'
    },
    'created': {
        'can_be_None': False,
        'type': 'int'
    },
    'updated': {
        'can_be_None': False,
        'type': 'int'
    },
    'original_url': {
        'can_be_None': True,
        'type': 'str'
    },
    'lastCrawlTime': {
        'can_be_None': False,
        'type': 'str'
    }
}

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

item_fields = [
    'id',
    'name',
    'source',  # 来自哪个网站
    'cat',  # 商品类型
    'detail_cat',  # 详细的类型
    'brand',  # 品牌
    'sales',  # 总销量
    'attributes',  # 商品属性材质列表
    'measurements',  # 规格尺寸
    'total_inventory',  # 总货存
    'original_price',  # 原价
    'current_price',  # 现价
    'about',  # 介绍文案
    'care',  # 保养方式
    'sku_list',  # SkuItem's list
    'images',  # 商品图片
    'description',  # 商品功能描述
    'url',  # 商品链接
    'video',  # 商品视频
    'is_deleted',
    'created',
    'updated',
    'original_url',  # 原始商品链接
    'lastCrawlTime',
    # 'currency'
]
sku_fields = [
    'attributes',  # SkuAttributesItem
    'inventory',  # 货存
    'original_price',  # 原价
    'current_price',  # 现价
    'imgs',
    'sku',
    'url',
]
sku_attr_fields = [
    'colour_img',  # 颜色的图片
    'colour',  # 颜色
    'size',  # 尺码
    'other',  # 其他可选择的地方，如沙发是否可折叠啊
]

strict_str_field = [
    'id',
    'name',
    'source',
    'cat',
    'detail_cat',
    'original_price',
    'current_price',
    'url',
    'lastCrawlTime'
]
str_field = [
    'brand',
    'about',
    'care',
    'description',
    'video'
]
int_field = [
    'sales',
    'total_inventory',
]
strict_int_field = [
    'created',
    'updated',
]
list_str_field = [
    'attributes',
    'measurements'
]

strict_list_str_field = [
    'images'
]

