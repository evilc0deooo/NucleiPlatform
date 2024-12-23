# -*- coding: utf-8 -*-

import json
import os
import thirdparty
from pymongo import MongoClient
from bson import ObjectId
from flask import jsonify
from config import Config
from services.logger import logger


class ConnMongo(object):
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(ConnMongo, cls).__new__(cls)
            cls._instance.conn = MongoClient(Config.MONGO_URL)
        return cls._instance


def conn_db(collection, db_name=None):
    conn = ConnMongo().conn
    if db_name:
        return conn[db_name][collection]

    else:
        return conn[Config.MONGO_DB][collection]


def get_project_yaml(project_id):
    """
    查询指定 nuclei 项目信息
    """
    project_data = conn_db('project').find_one({'_id': ObjectId(project_id)})
    return project_data


def get_project_zombie(project_id):
    """
    查询指定 zombie 项目信息
    """
    project_data = conn_db('zombie_project').find_one({'_id': ObjectId(project_id)})
    return project_data


def get_project_data(page_size, page_index):
    """
    nuclei 项目视图翻页
    :param page_size: 页面数量
    :param page_index: 页面索引
    """
    offset = (page_index - 1) * page_size
    project_data = conn_db('project').find().sort('date', -1).skip(offset).limit(page_size)
    project_list = [
        dict(
            project_id=str(project.get('_id')),
            project_name=project.get('project_name'),
            project_description=project.get('project_description'),
            nuclei_template_yaml=project.get('nuclei_template_yaml'),
            nuclei_template_tags=project.get('nuclei_template_tags'),
            nuclei_proxy=project.get('nuclei_proxy'),
            nuclei_severity=project.get('nuclei_severity'),
            date=project.get('date')
        )
        for project in project_data
    ]

    return project_list


def get_zombie_project_data(page_size, page_index):
    """
    zombie 项目视图翻页
    :param page_size: 页面数量
    :param page_index: 页面索引
    """
    offset = (page_index - 1) * page_size
    project_data = conn_db('zombie_project').find().sort('date', -1).skip(offset).limit(page_size)
    project_list = [
        dict(
            project_id=str(project.get('_id')),
            project_name=project.get('project_name'),
            project_description=project.get('project_description'),
            service=project.get('service'),
            user_dict=project.get('user_dict'),
            pass_dict=project.get('pass_dict'),
            date=project.get('date')
        )
        for project in project_data
    ]

    return project_list


def get_nuclei_data(draw, start, length, project_id='ALL'):
    """
    获取 nuclei 扫描结果
    """
    if project_id != 'ALL':
        data = conn_db('nuclei_ret').find({'project_id': project_id}).skip(start).limit(length)
        nuclei_vul_total = conn_db('nuclei_ret').count_documents({'project_id': project_id})
    else:
        data = conn_db('nuclei_ret').find().skip(start).limit(length)
        nuclei_vul_total = conn_db('nuclei_ret').count_documents({})  # 获取集合中所有文档的计数

    result = {
        'draw': draw,
        'recordsTotal': nuclei_vul_total,
        'recordsFiltered': nuclei_vul_total,
        'data': [{
            'id': str(item['_id']),
            'project_id': item['project_id'],
            'template_url': item['template_url'],
            'template_id': item['template_id'],
            'vuln_name': item['vuln_name'],
            'vuln_severity': item['vuln_severity'],
            'vuln_url': item['vuln_url'],
            'curl_command': item['curl_command'],
            'target': item['target']
        } for item in data]
    }

    return jsonify(result)


def get_zombie_data(draw, start, length, project_id='ALL'):
    """
    获取 zombie 扫描结果
    """
    if project_id != 'ALL':
        data = conn_db('zombie_ret').find({'project_id': project_id}).skip(start).limit(length)
        zombie_ret_total = conn_db('zombie_ret').count_documents({'project_id': project_id})
    else:
        data = conn_db('zombie_ret').find().skip(start).limit(length)
        zombie_ret_total = conn_db('zombie_ret').count_documents({})  # 获取集合中所有文档的计数

    result = {
        'draw': draw,
        'recordsTotal': zombie_ret_total,
        'recordsFiltered': zombie_ret_total,
        'data': [{
            'id': str(item['_id']),
            'project_id': item['project_id'],
            'ip': item['ip'],
            'port': item['port'],
            'service': item['service'],
            'username': item['username'],
            'password': item['password'],
            'ok': item['OK'],
        } for item in data]
    }

    return jsonify(result)


def get_nodes_data(draw, start, length):
    """
    获取所有 Agent 节点信息
    """
    data = conn_db('nodes').find({}).skip(start).limit(length)
    nodes_total = conn_db('nodes').count_documents({})

    result = {
        'draw': draw,
        'recordsTotal': nodes_total,
        'recordsFiltered': nodes_total,
        'data': [{
            'id': str(item['_id']),
            'node_name': item['node_name'],
            'date': item['date']
        } for item in data]
    }

    return jsonify(result)


def download_nuclei_data(project_id='ALL'):
    """
    使用 mongoexport 导出, 防止结果过多卡死
    """
    filename = os.path.join(thirdparty.TMP_PATH, f'{project_id}_{thirdparty.random_choices()}.csv')
    if thirdparty.get_architecture() == 'ARM':
        mongoexport_bin = thirdparty.MONGOEXPORT_ARM_BIN
    else:
        mongoexport_bin = thirdparty.MONGOEXPORT_UNIX_BIN

    os.chmod(mongoexport_bin, 0o777)
    if project_id == 'ALL':
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.MONGO_DB}',
                          '--collection nuclei_ret',
                          '--type=csv --fields project_id,template_id,target,vuln_url,vuln_name,vuln_severity',
                          f'--out {filename}']
    else:
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.MONGO_DB}',
                          '--collection nuclei_ret',
                          "--query='{{\"project_id\": \"{_project_id}\"}}'".format(_project_id=project_id),
                          '--type=csv --fields project_id,template_id,target,vuln_url,vuln_name,vuln_severity',
                          f'--out {filename}']

    logger.info(' '.join(cmd_parameters))
    exec_ret = thirdparty.exec_system(cmd_parameters, timeout=96 * 60 * 60)

    if exec_ret == 'error':
        return False

    return filename


def download_zombie_data(project_id='ALL'):
    """
    使用 mongoexport 导出 zombie 结果, 防止结果过多卡死
    """
    filename = os.path.join(thirdparty.TMP_PATH, f'{project_id}_{thirdparty.random_choices()}.csv')
    if thirdparty.get_architecture() == 'ARM':
        mongoexport_bin = thirdparty.MONGOEXPORT_ARM_BIN
    else:
        mongoexport_bin = thirdparty.MONGOEXPORT_UNIX_BIN

    os.chmod(mongoexport_bin, 0o777)
    if project_id == 'ALL':
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.MONGO_DB}',
                          '--collection zombie_ret',
                          '--type=csv --fields project_id,ip,port,service,username,password,OK',
                          f'--out {filename}']
    else:
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.MONGO_DB}',
                          '--collection zombie_ret',
                          "--query='{{\"project_id\": \"{_project_id}\"}}'".format(_project_id=project_id),
                          '--type=csv --fields project_id,ip,port,service,username,password,OK',
                          f'--out {filename}']

    logger.info(' '.join(cmd_parameters))
    exec_ret = thirdparty.exec_system(cmd_parameters, timeout=96 * 60 * 60)

    if exec_ret == 'error':
        return False

    return filename


def download_domain_data(task_id='ALL', project_id=None):
    """
    使用 mongoexport 导出, 防止结果过多卡死
    """
    filename = os.path.join(thirdparty.TMP_PATH, f'{task_id}_{thirdparty.random_choices()}.csv')
    if thirdparty.get_architecture() == 'ARM':
        mongoexport_bin = thirdparty.MONGOEXPORT_ARM_BIN
    else:
        mongoexport_bin = thirdparty.MONGOEXPORT_UNIX_BIN

    os.chmod(mongoexport_bin, 0o777)
    if project_id:
        # 根据项目 ID 导出任务域名资产
        _task_data = conn_db('task', db_name=Config.API_MONGO_DB).find({'project_id': project_id})
        _task_id_list = [str(doc['_id']) for doc in _task_data]
        if not _task_id_list:
            return False

        query = f'{{"task_id": {{"$in": {json.dumps(_task_id_list)}}}}}'

        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection domain',
                          f'--query=\'{query}\'',
                          '--type=csv --fields fld,domain,record,type,ips,task_id,source',
                          f'--out {filename}']

    elif task_id == 'ALL':
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection domain',
                          '--type=csv --fields fld,domain,record,type,ips,task_id,source',
                          f'--out {filename}']

    else:
        cmd_parameters = [f'{mongoexport_bin}',
                          '--host=localhost',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection domain',
                          "--query='{{\"task_id\": \"{_task_id}\"}}'".format(_task_id=task_id),
                          '--type=csv --fields fld,domain,record,type,ips,task_id,source',
                          f'--out {filename}']

    logger.info(' '.join(cmd_parameters))
    exec_ret = thirdparty.exec_system(cmd_parameters, timeout=96 * 60 * 60)

    if exec_ret == 'error':
        return False

    return filename


def download_site_data(task_id='ALL', project_id=None):
    """
    使用 mongoexport 导出, 防止结果过多卡死
    """
    filename = os.path.join(thirdparty.TMP_PATH, f'{task_id}_{thirdparty.random_choices()}.csv')
    if thirdparty.get_architecture() == 'ARM':
        mongoexport_bin = thirdparty.MONGOEXPORT_ARM_BIN
    else:
        mongoexport_bin = thirdparty.MONGOEXPORT_UNIX_BIN

    os.chmod(mongoexport_bin, 0o777)

    if project_id:
        # 根据项目 ID 导出文件泄露资产
        _task_data = conn_db('task', db_name=Config.API_MONGO_DB).find({'project_id': project_id})
        _task_id_list = [str(doc['_id']) for doc in _task_data]
        if not _task_id_list:
            return False

        query = f'{{"task_id": {{"$in": {json.dumps(_task_id_list)}}}}}'

        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection site',
                          f'--query=\'{query}\'',
                          '--type=csv --fields fld,site,hostname,ip,title,status,http_server,body_length,finger,tag,task_id',
                          f'--out {filename}']

    elif task_id == 'ALL':
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection site',
                          '--type=csv --fields fld,site,hostname,ip,title,status,http_server,body_length,finger,tag,task_id',
                          f'--out {filename}']

    else:
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection site',
                          "--query='{{\"task_id\": \"{_task_id}\"}}'".format(_task_id=task_id),
                          '--type=csv --fields fld,site,hostname,ip,title,status,http_server,body_length,finger,tag,task_id',
                          f'--out {filename}']

    logger.info(' '.join(cmd_parameters))
    exec_ret = thirdparty.exec_system(cmd_parameters, timeout=96 * 60 * 60)
    if exec_ret == 'error':
        return False

    return filename


def download_file_leak_data(task_id='ALL', project_id=None):
    """
    使用 mongoexport 导出, 防止结果过多卡死
    """
    filename = os.path.join(thirdparty.TMP_PATH, f'{task_id}_{thirdparty.random_choices()}.csv')
    if thirdparty.get_architecture() == 'ARM':
        mongoexport_bin = thirdparty.MONGOEXPORT_ARM_BIN
    else:
        mongoexport_bin = thirdparty.MONGOEXPORT_UNIX_BIN

    os.chmod(mongoexport_bin, 0o777)

    if project_id:
        # 根据项目 ID 导出任务站点资产
        _task_data = conn_db('task', db_name=Config.API_MONGO_DB).find({'project_id': project_id})
        _task_id_list = [str(doc['_id']) for doc in _task_data]
        if not _task_id_list:
            return False

        query = f'{{"task_id": {{"$in": {json.dumps(_task_id_list)}}}}}'

        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection file_leak',
                          f'--query=\'{query}\'',
                          '--type=csv --fields title,url,content_length,status_code,site,task_id',
                          f'--out {filename}']

    elif task_id == 'ALL':
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection file_leak',
                          '--type=csv --fields title,url,content_length,status_code,site,task_id',
                          f'--out {filename}']

    else:
        cmd_parameters = [f'{mongoexport_bin}',
                          f'--host={Config.MONGO_HOST}',
                          f'--port={Config.MONGO_PORT}',
                          f'--username={Config.MONGO_USERNAME}',
                          f'--password={Config.MONGO_PWD}',
                          f'--authenticationDatabase={Config.MONGO_AUTH_DB}',
                          f'--db {Config.API_MONGO_DB}',
                          '--collection file_leak',
                          "--query='{{\"task_id\": \"{_task_id}\"}}'".format(_task_id=task_id),
                          '--type=csv --fields title,url,content_length,status_code,site,task_id',
                          f'--out {filename}']

    logger.info(' '.join(cmd_parameters))
    exec_ret = thirdparty.exec_system(cmd_parameters, timeout=96 * 60 * 60)
    if exec_ret == 'error':
        return False

    return filename


def delete_project(project_id):
    """
    指定 nuclei 项目删除
    """
    try:
        project_data = conn_db('project').find_one({'_id': ObjectId(project_id)})
        if not project_data:
            logger.error(f'{project_id} nuclei 项目不存在')
            return False
        conn_db('project').delete_one({'_id': ObjectId(project_id)})
        logger.info(f'删除 {project_id} nuclei 项目成功')
        return True
    except Exception as e:
        logger.error(f'删除 {project_id} nuclei 项目失败 -> {e}')
        return False


def delete_zombie_project(project_id):
    """
    指定 zombie 项目删除
    """
    try:
        project_data = conn_db('zombie_project').find_one({'_id': ObjectId(project_id)})
        if not project_data:
            logger.error(f'{project_id} zombie 项目不存在')
            return False
        conn_db('zombie_project').delete_one({'_id': ObjectId(project_id)})
        logger.info(f'删除 {project_id} zombie 项目成功')
        return True
    except Exception as e:
        logger.error(f'删除 {project_id} zombie 项目失败 -> {e}')
        return False


if __name__ == '__main__':
    download_file_leak_data(task_id='6017edf36591e76d16171b65')
