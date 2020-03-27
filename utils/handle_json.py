# -*- coding: utf-8 -*-
# @Time : 2020/3/27 0:41
# @Author : wangmengmeng
import json
from config.cfg import *


def write_data(data, filename):
    file_path = os.path.join(config_path, filename)
    # print(file_path)
    with open(file_path, 'w', encoding='utf8') as f:  # 如果json文件不存在会自动创建
        json.dump(data, f,indent=4,ensure_ascii=False)
        print("数据写入json文件完成...")


if __name__ == '__main__':
    dict_test = {}
    write_data(dict_test, 'data_test2.json')
