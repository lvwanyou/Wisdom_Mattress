# -*- coding: utf-8 -*-
import falcon
import json
import datetime
from application import arith
from application.analyser import Analyser
from application.statisticsForMonth_api import StatisticsForMonth


class StageHealthScoreApi:

    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.statisticsForMonth = StatisticsForMonth(self.db)
        self.StageHealthStat = {'daily_health_stat': {}, 'average_health_stat': {}}

    def on_get(self, req, resp, user_id, date):
        """
        获取日健康评分
        通过上一个月的平均值跟该天的进行比较
        比较的方式为：  暂定
        """
        total_score = 100  # 设置日健康评分满分
        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAT_ALGORI_VERSION:
            self.analyser.analyse(user_id, date)  # analysis 计算date天的睡眠状态数据 和分析数据
            data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        sleep_stat = data_from_db.get('data')

        # 将月份置为上一个月份
        last_month_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        dayscount = datetime.timedelta(days=last_month_date.day)
        last_month_date = last_month_date - dayscount
        last_month_date_format = str(last_month_date.year) + "-" + str(last_month_date.month)
        self.sleep_statLastMonth = self.statisticsForMonth.get_sleep_statForMonth(user_id, last_month_date_format)

        """
           当天的健康数据
        """
        self.StageHealthStat['daily_health_stat']['duration'] = sleep_stat['duration']
        self.StageHealthStat['daily_health_stat']['sleepTime'] = str(
            round((sleep_stat['duration'][1] - sleep_stat['duration'][0]).seconds * 1.0 / 60, 2)) + "min"
        self.StageHealthStat['daily_health_stat']['firstAwakeLight'] = int(
            round(sleep_stat['firstAwakeLight'] * 1.0 / 60))
        self.StageHealthStat['daily_health_stat']['offBedFrequency'] = sleep_stat['offbed']
        self.StageHealthStat['daily_health_stat']['heartbeat'] = sleep_stat['heartbeat']
        self.StageHealthStat['daily_health_stat']['breath'] = sleep_stat['breath']
        # 格式化睡眠范围
        for index in range(len(self.StageHealthStat['daily_health_stat']['duration'])):
            self.StageHealthStat['daily_health_stat']['duration'][index] = \
            self.StageHealthStat['daily_health_stat']['duration'][index].isoformat()
        """
        根据上一个月计算出的平均健康数据
        """
        # 月均入睡时间暂无
        self.StageHealthStat['average_health_stat']['averSleepDuration'] = [0] * int(2)

        #  平均睡眠时间（unit:min）//将睡眠时间转化为分钟，保留小数点后两位
        self.StageHealthStat['average_health_stat']['averSleepTime'] = str(round((float(
            self.sleep_statLastMonth['sleepRange'][1]) + float(self.sleep_statLastMonth['sleepRange'][0])) * 1.0 / 2,
                                                                                 2)) + "min"
        #  平均入睡时间（unit:min）
        self.StageHealthStat['average_health_stat']['averFirstAwakeLight'] = self.sleep_statLastMonth[
            'AverFirstAwakeLight']
        # 平均离床次数
        self.StageHealthStat['average_health_stat']['averOffBedFrequency'] = self.sleep_statLastMonth[
            'AverOffBedFrequency']
        # 平均心率
        self.StageHealthStat['average_health_stat']['averHeartbeat'] = sum(
            self.sleep_statLastMonth['heartbeat']) / self.statisticsForMonth.DaysValidity
        # 平均呼吸频率
        self.StageHealthStat['average_health_stat']['averBreath'] = sum(
            self.sleep_statLastMonth['breath']) / self.statisticsForMonth.DaysValidity
        print (self.StageHealthStat)
        resp.body = json.dumps(self.StageHealthStat)
        resp.status = falcon.HTTP_200
