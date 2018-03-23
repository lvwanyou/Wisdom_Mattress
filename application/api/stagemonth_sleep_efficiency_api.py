# -*- coding: utf-8 -*-
import falcon
import json

from datetime import *
import calendar
from dateutil.parser import *

from application.statmonth_analyser import StatMonthAnalyser


class StageMonthSleepEfficiencyApi:

    def __init__(self, db):
        self.db = db
        self.statMonth_analyser = StatMonthAnalyser(db)
        self.sleep_statForMonth = {}

    # 初始化接口参数
    def init_param(self, date):
        month_range = calendar.monthrange(date.year, date.month)  # 获取当前月的总天数
        self.sleep_statForMonth['offBedTime'] = [[] for i in range(int(month_range[1]))]
        return month_range

    def on_get(self, req, resp, user_id, date):
        date = parse(date)
        month_range = self.init_param(date)
        first_day = parse(str(date.year) + '-' + str(date.month) + '-01')
        days_validity = month_range[1]
        for i in range(0, days_validity):
            node_day = first_day + timedelta(days=i)
            node_day = node_day.strftime('%Y-%m-%d')  # 格式化日期格式
            self.sleep_statForMonth['offBedTime'][i] = self.statMonth_analyser.get_offbed_time(user_id,
                                                                                               node_day)  # 离床时间
        slee_efficiency_report = dict()
        # 夜间最长离床时间,平均离床时间
        slee_efficiency_report['aver_large_offbed_time'] = self.statMonth_analyser.get_aver_large_offbed_time(
            self.sleep_statForMonth['offBedTime'])
        # 最频繁离床时间段及次数
        values_temp = self.statMonth_analyser.get_offbed_time_point(self.sleep_statForMonth['offBedTime'])
        slee_efficiency_report['offbed_time_point'] = values_temp['offbed_time_point']

        # 夜间平均离床时间范围
        slee_efficiency_report['offbed_time_range'] = values_temp['offbed_time_range']

        # 夜间离床时间std
        slee_efficiency_report['offbed_time_std'] = values_temp['offbed_time_std']

        resp.body = json.dumps(slee_efficiency_report)
        resp.status = falcon.HTTP_200
