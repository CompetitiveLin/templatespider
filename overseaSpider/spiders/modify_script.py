import requests


def search(user_name):
    '''
    查找对应花名下, 还需要修改更新的脚本名
    :param user_name: 花名(如:涛儿)
    :return:
    '''
    data = {
        'password': 'weshop123',
        'user_name': user_name,
    }
    response = requests.post('http://20.81.114.208:9426/search_name', data=data, verify=False)
    print(response.json())


def update(name, Type, reason):
    '''
    当修改完代码之后, 需要对状态进行更新
    :param name: 脚本名
    :param type: 类型 如下
        type-1 网站失效
        type-2 本地能跑出数据(跑整个脚本可以, 单跑parse_detail不行)
        type-3 修改完成/需要重跑
        type-4 其他(需要填写原因)
    :param reason: 当type == 4的时候 填写原因
    :return:
    '''
    data = {
        'password': 'weshop123',
        'name': name,  # 脚本名
        'type': Type,  #
        'reason': reason,  # type = 4 一定要填, 否则不需要填写 .网站平台没有
    }
    response = requests.post('http://20.81.114.208:9426/save_log', data=data, verify=False)
    print(response.json())

if __name__ == '__main_':
    # 更新错误脚本的状态
    update(name='', Type=3, reason='')
    # 查看自己待修改更新的脚本名
    search(user_name='秃头')
