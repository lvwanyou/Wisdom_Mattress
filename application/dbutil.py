# -*- coding: utf-8 -*-
from dateutil.parser import *
from datetime import *

"""
histroy 中会存储最原始的数据，下一次响应记录事件是状态发生变化的时候。
{
    "_id" : ISODate("2017-07-31T18:04:05.549Z"),
    "breath" : 13,
    "state" : "normal",
    "sn" : "Z50995",
    "wet" : false,
    "heartbeat" : 70,
    "pos" : [ 
        7, 
        6
    ]
}
"""


# 得到date（start from 12:00 of the day）和其天数加一后的中午十二点的时候的 histroy的数据。
def get_source_data(db, user_id, date):
    start_time = parse(date) + timedelta(hours=12)
    cursor = db.history[user_id].find({'_id': {'$gte': start_time}}).sort([('_id', 1)]).limit(1)  # 得到当前天数
    if cursor.count() == 0:
        return cursor, None
    first_data_time = cursor[0]['_id']
    begin_interpolate = None
    print("---------------the gap between first_data_time and start_time---------------  ", (first_data_time - start_time).seconds)
    if (first_data_time - start_time).seconds > 300:
        cursor = db.history[user_id].find({'_id': {'$lt': start_time}}).sort([('_id', -1)]).limit(1)
        if cursor.count() == 1:
            begin_interpolate = cursor[0].copy()
            begin_interpolate['_id'] = start_time
    end_time = start_time + timedelta(days=1)
    condition = {'_id': {'$gte': start_time, '$lte': end_time}}
    cursor = db.history[user_id].find(condition)
    return cursor, begin_interpolate


# 获取实际睡眠阶段数据 时间分段 根据实际睡眠阶段 "sleep_actual"
def get_trim_source_data(db, user_id, date, sleep_actual):
    if sleep_actual:
        start_time = sleep_actual[0]  # 睡眠开始
        end_time = sleep_actual[1]  # 睡眠结束
    else:
        start_time = parse(date) + timedelta(hours=12)  # 开始时间 当天12：00
        end_time = start_time + timedelta(days=1)  # 结束时间 第二天12：00
    condition = {'_id': {'$gte': start_time, '$lte': end_time}}
    cursor = db.history[user_id].find(condition)
    return cursor


def save_sleep_stage(db, algori_ver, user_id, date, sleep_stage):
    db.sleep_phase[user_id].update_one(
        {'_id': date},
        {'$set': {'_id': date, 'ver': algori_ver, 'data': sleep_stage}},
        upsert=True)


def save_sleep_stat(db, algori_ver, user_id, date, sleep_stat):
    db.sleep_stat[user_id].update_one(
        {'_id': date},
        {'$set': {'_id': date, 'ver': algori_ver, 'data': sleep_stat}},
        upsert=True)
