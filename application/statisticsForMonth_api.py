# -*- coding: utf-8 -*-
import falcon
import json
from datetime import *

import numpy
from dateutil.parser import *
import calendar

from analyser import Analyser
from statmonth_analyser import StatMonthAnalyser
from statistics_api import Statistics

import arith


class StatisticsForMonth:
    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.statistics = Statistics(self.db)
        self.sleep_statForMonth = {}
        self.DaysValidity = 0  # 用于计算各种分数的有效天数
        self.statMonth_analyser = StatMonthAnalyser(db)

    # 初始化接口参数
    def init_param(self, date):
        month_range = calendar.monthrange(date.year, date.month)  # 获取当前月的总天数
        self.DaysValidity = month_range[1]
        self.sleep_statForMonth['score'] = [0] * int(month_range[1] + 1)  # 声明 每日得分 list的大小
        self.sleep_statForMonth['sleepTime'] = [0] * int(month_range[1] + 1)  # 声明实际睡眠时间 list的大小
        self.sleep_statForMonth['offBedFrequency'] = [0] * int(month_range[1] + 1)  # 声明 离床次数 list的大小
        self.sleep_statForMonth['offBedTime'] = [0] * list(month_range[1] + 1)  # 声明 离床时间 list的大小
        self.sleep_statForMonth['onBedTime'] = [0] * int(month_range[1] + 1)  # 声明在床时间 list 的大小
        self.sleep_statForMonth['deepSleepTime'] = [0] * int(month_range[1] + 1)  # 声明深睡时间 list 的大小
        self.sleep_statForMonth['heartbeat'] = [0] * int(month_range[1] + 1)  # 声明心率（次/分） list 的大小
        self.sleep_statForMonth['breath'] = [0] * int(month_range[1] + 1)  # 声明呼吸频率（次/分） list 的大小
        return month_range

    # 初始化data_from_db
    def init_date_from_db(self, user_id, date):
        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAT_ALGORI_VERSION:
            self.analyser.analyse(user_id, date)  # analysis 计算date天的睡眠状态数据 和分析数据

        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        return data_from_db

    # 提取数据不可用的天数，对不可用数据统一设置
    def set_param_invalid(self, day):
        self.sleep_statForMonth['score'][day] = 0
        self.sleep_statForMonth['sleepTime'][day] = 0
        self.sleep_statForMonth['offBedFrequency'][day] = 0
        self.sleep_statForMonth['onBedTime'][day] = 0
        self.sleep_statForMonth['deepSleepTime'][day] = 0
        self.sleep_statForMonth['heartbeat'][day] = 0
        self.sleep_statForMonth['breath'][day] = 0

    #  method: 封装获取指定date的score
    #  指定day的 score  :   self.sleep_statForMonth['score'][day]
    #  指定day的 sleep_time（有效睡眠时间）:   self.sleep_statForMonth['sleep_time'][day]
    #  指定day的 offBedFrequency（离床次数）:    self.sleep_statForMonth['offBedFrequency'][day]
    #  指定day的 onBedTime（在床时间）:    self.sleep_statForMonth['onBedTime'][day]
    #  指定day的 deepSleepTime（深睡时间）:    self.sleep_statForMonth['deepSleepTime'][day]
    #  指定day的 heartbeat（声明心率（次/分））:    self.sleep_statForMonth['heartbeat'] [day]
    #  指定day的 breath（呼吸频率（次/分））:   self.sleep_statForMonth['breath'] [day]
    def get_day_score(self, user_id, date, date_from_db):
        day = parse(date).day  # 获取参数day

        sleep_stat_for_day = date_from_db.get('data')
        if sleep_stat_for_day is None or sleep_stat_for_day['validity'] is False:  # 根据该月的有效天数获取score  ，判断字段：validity
            self.DaysValidity -= 1
            sleep_stat_for_day['score'] = 0
            self.set_param_invalid(day)
            return

        sleep_stat_for_day['validity'] = True
        # 将秒换算为分钟
        sleep_stat_for_day['awake'] = sleep_stat_for_day['awake'] / 60
        sleep_stat_for_day['light'] = sleep_stat_for_day['light'] / 60
        sleep_stat_for_day['deep'] = sleep_stat_for_day['deep'] / 60
        record_time = sleep_stat_for_day['awake'] + sleep_stat_for_day['light'] + sleep_stat_for_day['deep']  # 记录在床时间

        if record_time < 3 * 60:
            sleep_stat_for_day['validity'] = False
            self.DaysValidity -= 1
            self.set_param_invalid(day)
            return

        if sleep_stat_for_day.get('firstAwakeLight') is not None:
            sleep_stat_for_day['firstAwakeLight'] = sleep_stat_for_day['firstAwakeLight'] / 60
            sleep_stat_for_day['score'], sleep_stat_for_day['sleepEval'] = self.statistics.get_sleep_assess(
                sleep_stat_for_day['offbed'],
                sleep_stat_for_day['firstAwakeLight'],
                sleep_stat_for_day['awake'],
                sleep_stat_for_day['light'],
                sleep_stat_for_day['deep'])
            # 有效数据设置
            self.sleep_statForMonth['score'][day] = sleep_stat_for_day['score']
            self.sleep_statForMonth['sleepTime'][day] = sleep_stat_for_day['light'] + sleep_stat_for_day['deep']
            self.sleep_statForMonth['offBedFrequency'][day] = sleep_stat_for_day['offbed']
            self.sleep_statForMonth['onBedTime'][day] = sleep_stat_for_day['light'] + sleep_stat_for_day['deep'] + \
                                                        sleep_stat_for_day['awake'] + sleep_stat_for_day[
                                                            'firstAwakeLight']
            self.sleep_statForMonth['deepSleepTime'][day] = sleep_stat_for_day['deep']
            self.sleep_statForMonth['heartbeat'][day] = sleep_stat_for_day['heartbeat']
            self.sleep_statForMonth['breath'][day] = sleep_stat_for_day['breath']
        else:
            sleep_stat_for_day['score'] = None
            sleep_stat_for_day['sleepEval'] = ['数据无效,无法进行评价']
            self.set_param_invalid(day)
        if sleep_stat_for_day['duration']:
            sleep_stat_for_day['duration'][0] = str(sleep_stat_for_day['duration'][0])
            sleep_stat_for_day['duration'][1] = str(sleep_stat_for_day['duration'][1])

    #  拿到每月中每天的睡眠的有效时间，然后再得到对应的标准差和平均值，设定正常睡眠范围
    def get_sleep_range(self):
        sleep_range = numpy.std(self.statMonth_analyser.get_valid_sleep_times(self.sleep_statForMonth['sleepTime']),
                                ddof=0)  # 由于样本容量较小，故用有偏标准差进行计算。
        sleep_average_time = sum(self.sleep_statForMonth['sleepTime']) / self.DaysValidity
        self.sleep_statForMonth['sleepRange'] = [0] * int(2)  # 声明 score list的大小
        if self.sleep_statForMonth['sleepRange']:
            self.sleep_statForMonth['sleepRange'][0] = str(sleep_average_time - sleep_range)
            self.sleep_statForMonth['sleepRange'][1] = str(sleep_average_time + sleep_range)

    def on_get(self, req, resp, user_id, date):
        date = parse(date)
        month_range = self.init_param(date)
        first_day = parse(str(date.year) + '-' + str(date.month) + '-01')
        days_validity = month_range[1]
        for i in range(0, days_validity):
            node_day = first_day + timedelta(days=i)
            node_day = node_day.strftime('%Y-%m-%d')  # 格式化日期格式
            date_from_db = self.init_date_from_db(user_id, node_day)  # 初始化data_from_db
            self.get_day_score(user_id, node_day, date_from_db)  # 根据每一天获取每一天的score ，算出平均值，为月报的分数

        self.sleep_statForMonth['averScore'] = sum(self.sleep_statForMonth['score']) / self.DaysValidity  # 月报平均得分
        self.get_sleep_range()  # 获取月睡眠时间段

        self.sleep_statForMonth['LargestOffBedFrequency'] = max(
            self.sleep_statForMonth['offBedFrequency'])  # 获取最大离床次数   ###############################  error
        self.sleep_statForMonth['AverOffBedFrequency'] = sum(self.statMonth_analyser.get_valid_sleep_times(
            self.sleep_statForMonth['offBedFrequency'])) / self.DaysValidity  # 获取平均离床时间
        # 睡眠效率: 实际睡眠时间和在床时间的比值  (即 (deep_sleep+ light_sleep)/(light+firstAwakeLight+deep+awake))
        self.sleep_statForMonth['sleepEfficiency'] = str(round(
            ((sum(self.sleep_statForMonth['sleepTime']) * 1.0) / (sum(
                self.sleep_statForMonth['onBedTime']) * 1.0)), 4) * 100) + '%'
        # 深睡效率：深睡时间与实际睡眠时间的比值 (即 deep_sleep/deep_sleep+ light_sleep)
        self.sleep_statForMonth['deepSleepEfficiency'] = str(round(
            ((sum(self.sleep_statForMonth['deepSleepTime']) * 1.0) / (sum(
                self.sleep_statForMonth['sleepTime']) * 1.0)), 4) * 100) + '%'
        # 平均心率
        self.sleep_statForMonth['averHeartbeat'] = sum(self.sleep_statForMonth['heartbeat']) / self.DaysValidity
        # 呼吸频率
        self.sleep_statForMonth['averBreath'] = sum(self.sleep_statForMonth['breath']) / self.DaysValidity

        # 离床时间
        self.sleep_statForMonth['offBedTime']
        # 方面有问题，这里的offbed为offbed_frequency   ;算出offbedTime,完成作息规律性计算；

        """
        
        """
        #    sleep_stat_mon = {'lv': 'wan'}
        resp.body = json.dumps(self.sleep_statForMonth)
        resp.status = falcon.HTTP_200
