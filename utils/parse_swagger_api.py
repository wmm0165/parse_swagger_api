# -*- coding: utf-8 -*-
# @Time : 2020/3/25 11:47
# @Author : wangmengmeng
import os
import json
import requests
import hashlib
from pprint import pprint
from config.cfg import *
from utils.handle_json import write_data


class ParseJson:
    def __init__(self):
        # 定义测试用例集格式
        self.http_suite = {"config": {"name": "", "base_url": "", "variables": {}},
                           "testcases": []}
        # 定义测试用例格式
        self.http_testcase = {"name": "", "testcase": "", "variables": {}}

    def login(self):
        session = requests.session()
        m = hashlib.md5()
        m.update(password.encode())
        passwd = m.hexdigest()
        params = {"name": username, "password": passwd}
        headers = {'Content-Type': "application/json"}
        res = session.post('http://{}:9999//syscenter/api/v1/currentUser'.format(host), data=json.dumps(params),
                           headers=headers).json()  # 访问swagger需要事先登录
        pprint(res)
        return session

    def parse_json_data(self):
        s = self.login()
        res = None
        try:
            res = s.get('http://{}:{}/v2/api-docs'.format(host, port)).json()
            # write_data(res, 'data.json')


        except Exception as e:
            print("地址请求错误，异常如下：{}".format(e))

        self.data = res['paths']  # 获取接口数据
        # pprint(self.data)
        self.definitions = res['definitions']
        self.title = res['info']['title']
        self.http_suite['config']['name'] = self.title  # 在初始化用例集字典更新值
        self.http_suite['config']['base_url'] = 'http://' + res['host']
        self.tags_list = [tag_dict['name'] for tag_dict in res['tags']]  # 测试用例的标签
        pprint(self.http_suite)
        i = 0
        for tag in self.tags_list:
            self.http_suite['testcases'].append({"name": "", "testcase": "", "variables": {}})
            self.http_suite['testcases'][i]['name'] = tag
            self.http_suite['testcases'][i]['testcase'] = 'testcases/' + tag + '.json'
            i += 1
        if not os.path.exists(suite_path):
            os.mkdir(suite_path)
        testsuite_json_path = os.path.join(suite_path, '{}_testsuites.json'.format(self.title))
        print(testsuite_json_path)
        write_data(self.http_suite, testsuite_json_path)
        print(self.tags_list)
        for tag in self.tags_list:
            self.http_case = {"config": {"name": "", "base_url": "", "variables": {}}, "teststeps": []}

            for key, value in res['paths'].items():
                print(key, value)
                for method in list(value.keys()):
                    params = value[method]
                    print(params)
                    if params['tags'][0] == tag:
                        self.http_case['config']['name'] = params['tags'][0]
                        self.http_case['config']['base_url'] = 'http://' + res['host']
                        case = self.parse_params(params, key, method, tag)
                        self.http_case['teststeps'].append(case)
            if not os.path.exists(testcases_path):
                os.mkdir(testcases_path)
            testcase_json_path = os.path.join(testcases_path, tag + '.json')
            write_data(self.http_case, testcase_json_path.replace("/", "_"))

    def parse_params(self, params, api, method, tag):
        # 定义接口数据格式
        http_interface = {"name": "", "variables": {},
                          "request": {"url": "", "method": "", "headers": {}, "json": {}, "params": {}}, "validate": [],
                          "output": []}
        # 测试用例的数据格式:
        http_api_testcase = {"name": "", "api": "", "variables": {}, "validate": [], "extract": [], "output": []}
        name = params['summary'].replace('/', '_')
        http_interface['name'] = name
        http_api_testcase['name'] = name
        http_api_testcase['api'] = 'api/{}/{}.json'.format(tag, name)
        http_interface['request']['method'] = method.upper()
        http_interface['request']['url'] = api.replace('{', '$').replace('}', '')
        parameters = params.get('parameters')  # 未解析的参数字典
        responses = params.get('responses')
        if not parameters:  # 确保参数字典存在
            parameters = {}
        for each in parameters:
            if each.get('in') == 'body':  # body 和 query 不会同时出现
                schema = each.get('schema')
                if schema:
                    ref = schema.get('$ref')
                    if ref:
                        param_key = ref.split('/', 2)[-1]  # 这个uri拆分，根据实际情况来取第几个/反斜杠
                        param = self.definitions[param_key]['properties']
                        for key, value in param.items():
                            if 'example' in value.keys():
                                http_interface['request']['json'].update({key: value['example']})
                            else:
                                http_interface['request']['json'].update({key: ''})

            elif each.get('in') == 'query':
                name = each.get('name')
                for key in each.keys():
                    if not 'example' in key:  # 取反，要把在query的参数写入json测试用例
                        http_interface['request']['params'].update({name: each[key]})

        for each in parameters:
            if each.get('in') == 'header':
                name = each.get('name')
                for key in each.keys():
                    if 'example' in key:
                        http_interface['request']['headers'].update({name: each[key]})
                    else:
                        if name == 'token':
                            http_interface['request']['headers'].update({name: '$token'})
                        else:
                            http_interface['request']['headers'].update({name: ''})

        for key, value in responses.items():
            schema = value.get('schema')
            if schema:
                ref = schema.get('$ref')
                if ref:
                    param_key = ref.split('/')[-1]
                    res = self.definitions[param_key]['properties']
                    i = 0
                    for k, v in res.items():
                        if 'example' in v.keys():
                            http_interface['validate'].append({"eq": []})
                            http_interface['validate'][i]['eq'].append('content.' + k)
                            http_interface['validate'][i]['eq'].append(v['example'])
                            http_api_testcase['validate'].append({"eq": []})
                            http_api_testcase['validate'][i]['eq'].append('content.' + k)
                            http_api_testcase['validate'][i]['eq'].append(v['example'])
                            i += 1
                else:
                    if len(http_interface['validate']) != 1:
                        http_interface['validate'].append({"eq": []})
            else:
                if len(http_interface['validate']) != 1:
                    http_interface['validate'].append({"eq": []})

            # 测试用例的请求参数为空字典，则删除这些key
        if http_interface['request']['json'] == {}:
            del http_interface['request']['json']

        if http_interface['request']['params'] == {}:
            del http_interface['request']['params']

            # 定义接口测试用例
        tags_path = os.path.join(api_path, tag).replace("/", "_")

        # 创建不存在的文件目录
        if not os.path.exists(api_path):
            os.mkdir(api_path)
        if not os.path.exists(tags_path):
            os.mkdir(tags_path)
        json_path = os.path.join(tags_path, http_interface['name'] + '.json')
        write_data(http_interface, json_path)  # 写入数据
        return http_api_testcase


if __name__ == '__main__':
    pa = ParseJson()
    # pa.login()
    pa.parse_json_data()
