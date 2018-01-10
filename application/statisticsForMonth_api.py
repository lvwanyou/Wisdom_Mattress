# -*- coding: utf-8 -*-
import falcon
import json
from datetime import *
from dateutil.parser import *
import calendar

from analyser import Analyser
from statistics_api import Statistics
import arith


class StatisticsForMonth:
    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.statistics = Statistics(self.db)
        self.sleep_statForMonth = {}
        self.DaysValidity = 0

    def get_day_score(self, user_id, date):
        day = parse(date).day  # 获取参数day
        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAT_ALGORI_VERSION:
            self.analyser.analyse(user_id, date)  # analysis 计算date天的睡眠状态数据 和分析数据
            data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})

        sleep_stat_for_day = data_from_db.get('data')
        if sleep_stat_for_day is None or sleep_stat_for_day['validity'] is False:  # 根据该月的有效天数获取score  ，判断字段：validity
            self.DaysValidity -= 1
            sleep_stat_for_day['score'] = 0
            self.sleep_statForMonth['score'][day] = 0
            return

        sleep_stat_for_day['validity'] = True
        # 将秒换算为分钟
        sleep_stat_for_day['awake'] = sleep_stat_for_day['awake'] / 60
        sleep_stat_for_day['light'] = sleep_stat_for_day['light'] / 60
        sleep_stat_for_day['deep'] = sleep_stat_for_day['deep'] / 60
        record_time = sleep_stat_for_day['awake'] + sleep_stat_for_day['light'] + sleep_stat_for_day['deep']

        if record_time < 3 * 60:
            sleep_stat_for_day['validity'] = False
            self.DaysValidity -= 1
            self.sleep_statForMonth['score'][day] = 0
            return

        if sleep_stat_for_day.get('firstAwakeLight') is not None:
            sleep_stat_for_day['firstAwakeLight'] = sleep_stat_for_day['firstAwakeLight'] / 60
            sleep_stat_for_day['score'], sleep_stat_for_day['sleepEval'] = self.statistics.get_sleep_assess(
                sleep_stat_for_day['offbed'],
                sleep_stat_for_day['firstAwakeLight'],
                sleep_stat_for_day['awake'],
                sleep_stat_for_day['light'],
                sleep_stat_for_day['deep'])
            self.sleep_statForMonth['score'][day] = sleep_stat_for_day['score']
        else:
            sleep_stat_for_day['score'] = None
            sleep_stat_for_day['sleepEval'] = ['数据无效,无法进行评价']
            self.sleep_statForMonth['score'][day] = 0
        if sleep_stat_for_day['duration']:
            sleep_stat_for_day['duration'][0] = str(sleep_stat_for_day['duration'][0])
            sleep_stat_for_day['duration'][1] = str(sleep_stat_for_day['duration'][1])

    def on_get(self, req, resp, user_id, date):
        date = parse(date)
        month_range = calendar.monthrange(date.year, date.month)  # 获取当前月的总天数
        self.sleep_statForMonth['score'] = [0] * int(month_range[1] + 1)  # 声明 score list的大小
        first_day = parse(str(date.year) + '-' + str(date.month) + '-01')
        days_validity = month_range[1]
        for i in range(0, days_validity):
            node_day = first_day + timedelta(days=i)
            node_day = node_day.strftime('%Y-%m-%d')  # 格式化日期格式
            print (node_day)
            self.get_day_score(user_id, node_day)     # 根据每一天获取每一天的score ，算出平均值，为月报的分数

        sleep_stat_mon = {'lv': 'wan'}
        resp.body = json.dumps(self.sleep_statForMonth)
        resp.status = falcon.HTTP_200
