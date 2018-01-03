# -*- coding: utf-8 -*-
from dateutil.parser import *
from datetime import *
import json
import falcon
import requests

import settings


class NursingAnalyser:

    def __init__(self, db):
        self.db = db

    # 获取翻身确认时间左右的原始数据
    def get_raw_data_by_nurse_time(self, db, user_id, date, recordtime):
        side_minutes = 10
        start_time = recordtime + timedelta(minutes=-side_minutes)
        end_time = recordtime + timedelta(minutes=side_minutes)
        condition = {'_id': {'$gte': start_time, '$lte': end_time}}
        cursor = self.db.history[user_id].find(condition)
        return cursor

    def get_moves_record(self, cursor):
        count = 0
        last_time = None
        last_state = None
        sum_mov = {}
        sum_mov_time = {}
        for item in cursor:
            current_time = item['_id']
            if last_state == 'moving':
                sum_mov[count] = (current_time - last_time).seconds
                sum_mov_time[count] = last_time
                count = count + 1
            last_time = current_time
            last_state = item['state']
        return sum_mov, sum_mov_time

    def have_turnover_nurse(self, sum_mov, sum_mov_time):
        convol_seconds = 120   # 卷积长度，即求和的最大秒数
        minhigh = 15   # 确认是翻身峰的最低阈值限制
        sumsec = {}

        for i in xrange(len(sum_mov_time) - 1):
            sumsec[i] = sum_mov[i]
            for j in xrange(i + 1, len(sum_mov_time)):
                if ((sum_mov_time[j] - sum_mov_time[i]).seconds < convol_seconds):
                    sumsec[i] += sum_mov[j]
                else:
                    break
            if sumsec[i] > minhigh:
                return True
        return False

    # 获取翻身护理时间配置
    def get_nurse_config_time(self, user_id):
        udm_endpoint = 'http://%s:%s/udm' % (
            settings.config['service']['udm']['host'],
            settings.config['service']['udm']['port'])
        user = requests.get(udm_endpoint + '/users/%s' % user_id)
        if user.status_code == 200:
            user = user.json()
        guardian_id = user['guardianId']
        patrol_endpoint = 'http://%s:%s/patrol' % (
            settings.config['service']['patrol']['host'],
            settings.config['service']['patrol']['port'])
        patrol_config = requests.get(patrol_endpoint + '/config/%s' % guardian_id)
        if patrol_config.status_code == 200:
            return patrol_config.json()

    # 计算指定日期的翻身护理间隔时间表
    def get_nurse_interval_list(self, nurse_config, date):
        start_time = parse('%s %s' % (date, nurse_config['beginTime']))
        end_time = parse('%s %s' % (date, nurse_config['endTime']))
        if start_time.hour < 12:
            start_time += timedelta(days=1)
        if end_time.hour <= 12:
            end_time += timedelta(days=1)

        nurseInterval = nurse_config.get('nurseInterval', 120)
        nurse_time_record = []
        for i in xrange(24):
            time_point = start_time + timedelta(minutes=i * nurseInterval)
            if time_point <= end_time:
                nurse_time_record.append(time_point)
            else:
                break
        return nurse_time_record

    def on_get(self, req, resp, user_id, date):
        nurse_config = self.get_nurse_config_time(user_id)
        nurse_time_interval_list = self.get_nurse_interval_list(nurse_config, date)
        condition = {
            'nursingTime': {
                '$gte': nurse_time_interval_list[0],
                '$lte': nurse_time_interval_list[-1]}}
        # 此处获取的是护理确认按钮的记录时间
        data_from_db = self.db.nursing_record[user_id].find(condition)
        nurse_time_record = []
        for i in data_from_db:
            nurse_time_record.append(i.get('nursingTime'))
        turnover_time_list = []
        for i in range(len(nurse_time_interval_list) - 1):
            for nurse_time in nurse_time_record:
                if nurse_time_interval_list[i] <= nurse_time <= nurse_time_interval_list[i + 1]:
                    move_record = self.get_raw_data_by_nurse_time(self.db, user_id, date, nurse_time)
                    sum_mov, sum_mov_time = self.get_moves_record(move_record)
                    nursed = self.have_turnover_nurse(sum_mov, sum_mov_time)
                    if nursed:
                        turnover_time_list.append(
                            {'id': str(nurse_time), 'nursingTime': str(nurse_time)})
                        break
        resp.body = json.dumps({'nursingRecord': turnover_time_list})
        resp.status = falcon.HTTP_200
