# templatespider
Spiders during working in weshop

python语法整理：
1. f'的用法，例如`value_temp = response.xpath(f'//div[@class="box"]/div[{i+1}]/select/option/text()').getall()`。{}里的内容不管是什么属性，都会转化成string
2. r'的用法，例如`re.sub(r'<.*?>', ' ', input_text)`，作用是使转义字符无效
3. 列表生成式的用法，例如`opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]`
4. 不能确定一个变量是NoneType还是由空格组成的字符串时，用下列表达式判断，例如`if not price or not price.strip():`。因为会先进行是否为NoneType的判断，如果非NoneType则可继续执行strip()函数判断是否为空格字符串。（考虑到NoneType执行strip()函数会报错）
5. re正则表达式的search()与findall()函数用法，例如`re.findall("\"jsonConfig\":\s?(\{.*?\}),\n", response.text)`，建议在使用函数时先用`replace('\n','')、replace('\t','')`函数将消去所有回车换行符
6. 固定两位小数显示（有时候会受float转string的影响，导致输出类似1.0000000003等现象的出现），例如`sku_info["current_price"] = '{:.2f}'.format(float(items["current_price"]) + add_price)`
7. strip()与split()函数的使用，前者用于移除字符串头尾指定的字符（默认为空格），后者指定分隔符对字符串进行切片。另外在使用split()函数时需要注意的一个细节，例如
```python
>>> s1 = 'abc sss '
>>> print(s1.split(' '))  # 在列表的最后会是一个空字符
['abc', 'sss', '']  
>>> s2 = 'abcTESTcba'
>>> print(s2.strip('abc'))
TEST
>>> print(s2.strip('cba'))  # 将参数中的每个字符与s2的头尾进行对比，与顺序无关
TEST
```
8.修改.gitignore后，把原上传的文件删除，使用以下命令:
```shell
git rm -r --cached .                 #清除缓存
git add .                            #重新按照ignore的规则add所有的文件
git commit -m "update .gitignore"    #提交和注释
```
9. scrapy库中`response.urljoin('')`,`response.xpath('').get()`
10. yield生成器的使用，具体参考yield_test.py文件
11. xpath的一些语法，（有待更新）
12. `demjson.decode()`和`json.loads()`（解析字符串）和`json.load()`（解析文件）的区别：A、可解析不规则的json数据，B、解析规则的字符串，C、解析文件里的json数据
13. s= [None]，type(s)为list，并非NoneType
14. join()的用法, `items["detail_cat"] = '/'.join(cat_list)`，列表里的元素拼接起来，并在每两个元素中间添加一个字符'/'
15. 函数`response.text`（没有括号）得到的是该网页的源码
16. pycharm里debug的使用！
17. 网页的源码有时候会和f12打开的elements里的内容不一样，以网页源码为准！
18. 在执行scrapy中的run函数（其实就相当于在命令行里打scrapy crawl xxx），会把所有爬虫脚本先加载一遍，如果在脚本文件夹里不添加`if __name__ == '__main__':`代码段，则也会执行相应代码，详见yield_test.py
19. post函数，例如`response = requests.post('http://20.81.114.208:9426/search_name', data=data, verify=False)`，如果在postman里模拟请求，data则是在body里添加，并非parameter
20. 将环境中的所有包全部列出并自动生成requirements.txt，建议配合虚拟环境使用：
```
pip freeze > requirements.txt
```
21. To be continued...










