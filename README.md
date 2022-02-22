# templatespider
Spiders during working in weshop

python语法整理：
1. f'的用法，例如value_temp = response.xpath(f'//div[@class="box"]/div[{i+1}]/select/option/text()').getall()。{}里的内容不管是什么属性，都会转化成string
2. r'的用法，例如re.sub(r'<.*?>', ' ', input_text)，作用是使转义字符无效
3. 列表生成式的用法，例如opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
4. 不能确定一个变量是NoneType还是由空格组成的字符串时，用下列表达式判断，例如if not price or not price.strip()。因为会先进行是否为NoneType的判断，如果非NoneType则可继续执行strip()函数判断是否为空格字符串。（考虑到NoneType执行strip()函数会报错）
5. re正则表达式的search()与findall()函数用法，例如re.findall("\"jsonConfig\":\s?(\{.*?\}),\n", response.text)，建议在使用函数时先用replace('\n','')、replace('\t','')函数将消去所有回车换行符
6. 固定两位小数显示（有时候会受float转string的影响，导致输出类似1.0000000003等现象的出现），例如sku_info["current_price"] = '{:.2f}'.format(float(items["current_price"]) + + add_price)
7. strip()与split()函数的使用，另外在使用split()函数时需要注意的一个细节，例如>>string = 'abc sss '；print(string.split(' '))----->['abc', 'sss', ''],最后一个是会出现空字符
8. scrapy库中response.urljoin(''),response.xpath('').get(),
9. yield生成器的使用，具体参考yield_test.py文件
10. xpath的一些语法，（有待更新）
11. demjson.decode()和json.loads()（解析字符串）和json.load()（解析文件）的区别：1、可解析不规则的json数据，2、解析规则的字符串，3、解析文件里的json数据
12. s= [None]，type(s)为list，并非NoneType
13. join()的用法, items["detail_cat"] = '/'.join(cat_list)，列表里的元素拼接起来，并在每两个元素中间添加一个字符'/'
14. response.text（没有括号）得到的是该网页的源码
15. pycharm里debug的使用！
16. 网页的源码有时候会和f12打开的elements里的内容不一样，以网页源码为准！
17. 在执行scrapy中的run函数（其实就相当于在命令行里打scrapy crawl xxx），会把所有爬虫脚本先加载一遍，如果在脚本文件夹里不添加（if __name__ == '__main__':）代码段，则也会执行相应代码，详见yield_test.py
18. post函数，例如response = requests.post('http://20.81.114.208:9426/search_name', data=data, verify=False)，如果在postman里模拟请求，data则是在body里添加，并非parameter
19. 修改.gitignore后，把原上传的文件删除，使用以下命令，git rm -r --cached . #清除缓存，并且注意有一个点 git add . #重新按照ignore的规则add所有的文件 git commit -m “update .gitignore” #提交和注释
20. 
21. 











