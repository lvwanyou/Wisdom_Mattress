# -*- coding: utf-8 -*-
from datetime import timedelta

import falcon
import json
import numpy as np
from application.statistics_api import Statistics
from dateutil import parser
from sklearn.naive_bayes import MultinomialNB
import datetime


class MultinomialNBScoreReasonable:

    def __init__(self, db):
        self.db = db
        self.statistics = Statistics(self.db)
        self.time_range = [0] * 2
        self.TIME_RANGE = 30  # 训练数据的范围

    # 设置train 的数据的日期范围:范围为一年
    def set_time_range(self, date):
        date_end = parser.parse(date) - timedelta(days=1)
        date_begin = (date_end - timedelta(days=self.TIME_RANGE))
        self.time_range[0] = date_begin
        self.time_range[1] = date_end

    # 导入原始数据；划定训练集
    def get_stat_and_train(self, resp, user_id, stat, input_ep):
        temp_array = []  # 特征训练集X
        score_array = []  # 类别训练集Y
        for i in range(0, self.TIME_RANGE):
            date = stat[0] + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            sleep_stat = self.statistics.get_sleep_stat(resp, user_id, date_str)
            if sleep_stat is not None and sleep_stat['validity'] == True:
                temp_sub_array = []
                temp_sub_array.append(sleep_stat['offbed'])
                temp_sub_array.append(sleep_stat['light'])
                temp_sub_array.append(sleep_stat['firstAwakeLight'])
                temp_sub_array.append(sleep_stat['deep'])
                temp_sub_array.append(sleep_stat['breath'])
                temp_sub_array.append(sleep_stat['awake'])
                duration = (datetime.datetime.strptime(sleep_stat['duration'][1],
                                                       '%Y-%m-%d %H:%M:%S.%f') - datetime.datetime.strptime(
                    sleep_stat['duration'][0], '%Y-%m-%d %H:%M:%S.%f'))
                duration = duration.days * 12 * 3600 + duration.seconds
                temp_sub_array.append(duration)
                temp_sub_array.append(sleep_stat['heartbeat'])
                temp_array.append(temp_sub_array)
                score_array.append(sleep_stat['score'])
        x = np.array(temp_array)
        y = np.array(score_array)
        nb = MultinomialNB(alpha=1.0, fit_prior=True)
        nb.fit(x, y)
        predict_score = nb.predict(np.array(input_ep))
        return predict_score, score_array

    # 获取测试输入数据
    def get_input_example(self, resp, user_id, date_str):
        sleep_stat = self.statistics.get_sleep_stat(resp, user_id, date_str)
        if sleep_stat is None:
            return None, None

        input_example = []
        input_sub_example = list()
        input_sub_example.append(sleep_stat['offbed'])
        input_sub_example.append(sleep_stat['light'])
        input_sub_example.append(sleep_stat['firstAwakeLight'])
        input_sub_example.append(sleep_stat['deep'])
        input_sub_example.append(sleep_stat['breath'])
        input_sub_example.append(sleep_stat['awake'])
        duration = (datetime.datetime.strptime(sleep_stat['duration'][1],
                                               '%Y-%m-%d %H:%M:%S.%f') - datetime.datetime.strptime(
            sleep_stat['duration'][0], '%Y-%m-%d %H:%M:%S.%f'))
        duration = duration.days * 12 * 3600 + duration.seconds
        input_sub_example.append(duration)
        input_sub_example.append(sleep_stat['heartbeat'])
        real_score = sleep_stat['score']
        input_example.append(input_sub_example)
        return input_example, real_score

    # 获取数据分析合理比率
    def get_score_rationality(self, predict_score, real_score):
        if predict_score >= real_score:
            return round(real_score * 1.0 / (predict_score * 1.0), 4)
        else:
            return round(predict_score * 1.0 / (real_score * 1.0), 4)

    def on_get(self, req, resp, user_id, date):
        self.set_time_range(date)
        input_ep, real_score = self.get_input_example(resp, user_id, date)
        if input_ep is None and real_score is None:
            resp.body = json.dumps("{该天日报数据无效 （validity : false）！}")
            resp.status = falcon.HTTP_200
            return
        predict_score, y = self.get_stat_and_train(resp, user_id, self.time_range, input_ep)
        for i in range(len(self.time_range)):
            self.time_range[i] = self.time_range[i].isoformat()
        rationality = self.get_score_rationality(predict_score, real_score)
        result = {'train_time_range': self.time_range,
                  'real_score': real_score,
                  'predict_score': predict_score[0],
                  'rationality': rationality,
                  'train_Y': y
                  }
        resp.body = json.dumps(result)
        resp.status = falcon.HTTP_200
