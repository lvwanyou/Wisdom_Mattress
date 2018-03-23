# -*- coding: utf-8 -*-
from datetime import timedelta

import application.dbutil
from dateutil import parser
from dateutil.parser import *
from application.analyser import Analyser
from application.arith import WORK_REST_SCHEDULE
import datetime
import copy


class StageRegularityAnalyser:

    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.work_rest_schedule = {}
        self.total_score = 0
        self.stage_results = {
            'offbed': 'offbed',  # 离床
            'offline': 'offline',  # 掉线
            'awake': 'onbed',  # 清醒时间（s）
            'light': 'onbed',  # 轻度睡眠时间（s）
            'deep': 'onbed'  # 深度睡眠时间（s）
        }
        self.sleep_stages_score = {}  # 保存各个阶段的作息评分

    # 根据最初数据来判断日作息规律性   从6:00  到 6:00 of the next day.
    def calc_sleep_regularity(self, user_id, date):
        # cursor, _ = dbutil.get_source_data(self.db, user_id, date)
        # 设置时间范围为从date 天的6:00 到第二天的6:00
        start_time = parse(date)
        end_time = start_time + timedelta(days=1)
        start_time = start_time + timedelta(hours=6)
        end_time = end_time + + timedelta(hours=6)
        time_range = [start_time, end_time]
        cursor = application.dbutil.get_trim_source_data(self.db, user_id, date, time_range)
        self.analyser.analyse_source_data(cursor)
        sleep_stages = self.analyser.get_sleep_stage()
        sleep_duration = self.analyser.get_sleep_interval(date, sleep_stages)

        if sleep_duration is None:
            return

        sleep_stages_regularity = sleep_stages
        for i in range(len(sleep_stages_regularity) - 1):
            try:
                if sleep_stages_regularity[i]['state'] == 'offbed':
                    # 标识睡眠期间的离床，只有进入了睡眠状态后的离床才认为是睡眠期间的离床
                    if sleep_stages_regularity[i - 1]['state'] in ('light', 'deep'):
                        sleep_stages_regularity[i]['afterSleep'] = True
                    elif sleep_stages_regularity[i - 1]['state'] == 'awake' and \
                            sleep_stages_regularity[i - 2]['state'] in ('light', 'deep'):
                        sleep_stages_regularity[i]['afterSleep'] = True
            except Exception:
                continue

        return sleep_stages_regularity

    # 将包含各种睡眠状态的作息规律性转化为对应的onBed/offBed/offLine
    # return : 转化对应状态后的sleep_stages
    def translate_sleep_stages(self, sleep_stages):
        stages_num = len(sleep_stages)
        sleep_stages_result = []
        b_sleep_duration = {}
        for i in xrange(stages_num):
            if len(sleep_stages_result) == 0:
                b_sleep_duration['state'] = self.stage_results[sleep_stages[i]['state']]
                b_sleep_duration['time'] = sleep_stages[i]['time']
                sleep_stages_result.append(b_sleep_duration.copy())
            else:
                if self.stage_results[sleep_stages[i]['state']] != self.stage_results[sleep_stages[i - 1]['state']]:
                    b_sleep_duration['state'] = self.stage_results[sleep_stages[i]['state']]
                    b_sleep_duration['time'] = sleep_stages[i]['time']
                    sleep_stages_result.append(b_sleep_duration.copy())
        return sleep_stages_result

    # 对获取的日作息规律性进行打分判断
    def get_daily_regularity_score(self, sleep_stages_result, date, totalScore):
        """
        养老院规律作息时间表有12个状态，判断得分方法如下：
        获取养老院某个状态的总的时间长度x1，判断该A状态是off_bed or on_bed;根据该时间段的实际A状态的时长x2; x2/x1 得到百分比
        然后  该状态的实际得分=该状态对应的 weight * totalScore * （ x2/x1）
        最后将所有状态累加
        :param sleep_stages_result:
        :return:作息规律总得分，作息规律各阶段得分
        """
        self.total_score = totalScore
        self.mend_work_rest_schedule(date)
        final_score = 0
        final_time = self.work_rest_schedule[('SLEEP', 'ONBED')][
            1]  # 作息结束时间为规律表中的'('SLEEP', 'ONBED')'的value[1]//即第二天的6:00
        for index in range(len(sleep_stages_result)):  # sleep_stages_result中time为struct类型
            if index == len(sleep_stages_result) - 1:
                final_score += self.deal_daily_regularity_stat(sleep_stages_result[index]['time'],
                                                               final_time,
                                                               sleep_stages_result[index]['state'])
            else:
                final_score += self.deal_daily_regularity_stat(sleep_stages_result[index]['time'],
                                                               sleep_stages_result[index + 1]['time'],
                                                               sleep_stages_result[index]['state'])
        return int(round(final_score)), self.sleep_stages_score  # 对结果进行四舍五入

    # 给养老院规律表加上对应的日期，同时转化为struct类型
    def mend_work_rest_schedule(self, date):
        self.work_rest_schedule = copy.deepcopy(WORK_REST_SCHEDULE)
        for key, value in self.work_rest_schedule.iteritems():
            self.sleep_stages_score[key[0]] = 0
            value = list(value)
            if key[0] == 'SLEEP':
                temp_time0 = datetime.datetime.strptime(value[0], "%H:%M")
                temp_time1 = datetime.datetime.strptime(value[1], "%H:%M")
                value[0] = parser.parse(date) + timedelta(hours=temp_time0.hour, minutes=temp_time0.minute)
                value[1] = parser.parse(date) + timedelta(days=1, hours=temp_time1.hour, minutes=temp_time1.minute)
            else:
                temp_time0 = datetime.datetime.strptime(value[0], "%H:%M")
                temp_time1 = datetime.datetime.strptime(value[1], "%H:%M")
                value[0] = parser.parse(date) + timedelta(hours=temp_time0.hour, minutes=temp_time0.minute)
                value[1] = parser.parse(date) + timedelta(hours=temp_time1.hour, minutes=temp_time1.minute)
            value = tuple(value)
            self.work_rest_schedule[key] = value

    # 根据某个实际作息状态的起始与终止时间，计算该状态的得分
    def deal_daily_regularity_stat(self, begin_time, end_time, state):
        """
        :param begin_time: 实际作息状态起始时间
        :param end_time: 实际作息状态终止时间
        :param state: 作息状态
        :return: 得分
        """
        for key, value in self.work_rest_schedule.iteritems():
            # 判断该状态实际时间段和作息规律表该时段有交集；无交集不做处理
            if value[0] <= begin_time < value[1] or value[0] < end_time <= value[1]:
                if begin_time < value[0]:
                    begin_time = value[0]
                if end_time > value[1]:
                    end_time = value[1]
                if key[1] == state.upper():
                    x1 = value[1] - value[0]
                    x2 = end_time - begin_time
                    # 将x1、x2转化为second
                    x1 = (x1.days * 24 * 60 * 60 + x1.seconds) * 1.0
                    x2 = (x2.days * 24 * 60 * 60 + x2.seconds) * 1.0
                    score = (value[2] * 1.0 / (len(self.work_rest_schedule) * 1.0)) * self.total_score * round(x2 / x1,
                                                                                                               4)
                    self.sleep_stages_score[key[0]] += score
                    return score
        self.sleep_stages_score[key[0]] += 0.0
        return 0.0
