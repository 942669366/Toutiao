import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import json
from multiprocessing import Pool
from hashlib import md5
import pymongo
import os
import re
MONGO_URL = 'localhost'
MONGO_DB = 'toutiao'
MONGO_TABLE = '街拍'
GROUP_START = 1
GROUP_END = 8
keyword = '街拍'
client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]
headers = {
    ':authority':'www.toutiao.com',
    ':method':'GET',
    ':path':'/a6659145182681760270/',
    ':scheme':'https',
    'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'accept-encoding':'gzip, deflate, br',
    'accept-language':'zh-CN,zh;q=0.9',
    'cache-control':'max-age=0',
    'cookie':'tt_webid=6657778164884751875; tt_webid=6657778164884751875; WEATHER_CITY=%E5%8C%97%E4%BA%AC; UM_distinctid=168eb3bb7a464f-05d6398b1e736a-3257487f-144000-168eb3bb7a54de; tt_webid=6657778164884751875; csrftoken=e1f4c4dba22848cc5ff44ca889f448b5; uuid="w:d0e4c3bc45fd4eccb97c648ddf5237df"; CNZZDATA1259612802=1816554133-1550130956-https%253A%252F%252Fwww.sogou.com%252F%7C1550474449; __tasessionId=kxssz87tf1550474694348',
    'referer':'https://www.toutiao.com/search/?keyword=python',
    'upgrade-insecure-requests':'1',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6821.400 QQBrowser/10.3.3040.400',
}

def get_page_index(offset,keyword):
    data = {
        'aid':24,
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': 20,
        'cur_tab': 1,
        'from':'search_tab',
        'pd': 'synthesis',
    }
    url = "https://www.toutiao.com/api/search/content/?" + urlencode(data)#将字典对象自动转换成url的请求参数
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()#如果使用response.text会出现中文乱码
        return None
    except RequestException:
        print("请求索引页出错")
        return None
def get_page_datale(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()#如果使用response.text会出现中文乱码
        return None
    except RequestException:
        print("请求索引页出错")
        return None
def parse_page_index(html):
    # data = json.loads(html)
    # if data and 'data' in data.keys():#返回data.keys()的所有的键名
    #     for item in data.keys('data'):
    #         yield item.get('article_url')
    if html.get('data'):
        for item in html.get('data'):
            yield item
def parse_data_detail(url):
    if url == None:
        yield None

    else:
        href = url.replace('group/', 'a')
        response = requests.get(href)
        # print(response.text)
        response.encoding = 'utf-8'
        image_list = re.findall(r'&quot;http:(.*?)&quot;',response.text,re.S)
        yield image_list
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False
def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)#content:表示返回的是二进制内容，tex:表示返回的是数据的文本信息
        return None
    except RequestException:
        print('请求图片出错',url)
        return None

def save_image(content):
    file_path = '{0}\{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')#os.getcwd()表示当前路径项目路径
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()
def image_for(image_list_url):
    image_list = []
    if image_list_url == None:
        yield 'null'
    else:
        for images_urls in image_list_url:
            if images_urls == None:
                continue
            for image_url in images_urls:
                images_urla = 'https:'+image_url
                # download_image(images_urla)
                image_list.append(images_urla)
            yield image_list
def main(affset):
    html = get_page_index(affset,keyword)
    for item in parse_page_index(html):
        title = item.get('title')
        url = item.get('article_url')
        if title == None and url == None:
            continue
        image_list_url = parse_data_detail(url)
        images = image_for(image_list_url)
        for image in images:
            if image == None:
                resoult = {
                    "title": title,
                    "url": url,
                    "image": 'null'
                }
                if resoult:
                    save_to_mongo(resoult)
            else:
                resoult = {
                    "title":title,
                    "url":url,
                    "image":image
                }
                if resoult:
                    save_to_mongo(resoult)




if __name__ == "__main__":
    groups = [x* 20 for x in range(GROUP_START,GROUP_END + 1)]
    pool = Pool()
    pool.map(main,groups)
