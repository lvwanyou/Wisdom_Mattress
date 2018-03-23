# -*- coding: utf-8 -*-
import falcon
import json
import arith

from application.analysis.stage_regularity_analyser import StageRegularityAnalyser
from analyser import Analyser


class Statistics:
    def __init__(self, db):
        self.db = db
        self.user_id = None
        self.date = None
        self.analyser = Analyser(self.db)
        self.stage_regularity_analyser = StageRegularityAnalyser(self.db)
        self.assess_text = {
            'score': {
                'best': '恭喜! 您的总体睡眠质量相当不错',
                'good': '您的总体睡眠质量尚可',
                'normal': '您的总体睡眠质量不佳，需要改善',
                'bad': '您的总体睡眠质量较差，需要改善'
            },
            'sleep_time': {
                'best': '您的有效睡眠时间为 {sleep_time_hour} 小时，处于正常范围之内',
                'good': '您的有效睡眠时间为 {sleep_time_hour} 小时，成年人至少应保持每天 7 个小时的睡眠',
                'normal': '您的有效睡眠时间为 {sleep_time_hour} 小时，成年人至少应保持每天 7 个小时的睡眠',
                'bad': '您的有效睡眠时间仅为 {sleep_time_hour} 小时，成年人至少应保持每天 7 个小时的睡眠',
                'error': '404'
            },
            'sleep_efficiency': {
                'good': '',
                'normal': '同时，您的睡眠效率不高，请注意改善',
                'bad': '同时，您的睡眠效率不高，请注意改善',
                'error': '404'
            },
            'first_light_time': {
                'good': '您的入睡时间为 {first_light_time_minute} 分钟，属正常',
                'normal': '您的入睡时间为 {first_light_time_minute} 分钟，是轻度失眠的体现。建议您入睡前可适当做睡前体操放松，减轻大脑兴奋状态',
                'bad': '您的入睡时间为 {first_light_time_minute} 分钟，是中度失眠的体现。可咨询医师帮助改善',
                'error': '404'
            },
            'deep_sleep_account': {
                'best': '您的深睡时间为 {deep_time_hour} 小时，约占有效睡眠时间的 {deep_sleep_percet}% ，属正常',
                'good': '您的深睡时间为 {deep_time_hour} 小时，约占有效睡眠时间的 {deep_sleep_percet}% ，属正常',
                'normal': '您的深睡时间为 {deep_time_hour} 小时，约占有效睡眠时间的 {deep_sleep_percet}% ，属不佳',
                'bad': '您的深睡时间为 {deep_time_hour} 小时，仅约占有效睡眠时间的 {deep_sleep_percet}% ，属不佳',
                'error': '404'
            },
            'off_bed_times': {
                'good': '',
                'normal': '',
                'bad': '此外，您夜间起床多于 5 次，属不佳',
                'error': '404'
            }
        }

        self.assess_level = {
            'score': {
                (90, None): ('best'),
                (80, 90): ('good'),
                (70, 80): ('normal'),
                (0, 70): ('bad')
            },
            'offbed': {
                (0, 3): ('good', 10),
                (3, 6): ('normal', 8),
                (6, None): ('bad', 2),
                (None, 0): ('error', 0)
            },
            'first_light_time': {
                (0, 60): ('good', 15),
                (60, 90): ('normal', 10),
                (90, None): ('bad', 5),
                (None, 0): ('error', 0)
            },
            'sleep_time': {
                (7 * 60, None): ('best', 20),
                (5 * 60, 7 * 60): ('good', 15),
                (3 * 60, 5 * 60): ('normal', 10),
                (0, 3 * 60): ('bad', 5),
                (None, 0): ('error', 0)
            },
            'deep_sleep_account': {
                (1, None): ('error', 0),
                (0.45, 1): ('best', 30),
                (0.35, 0.45): ('good', 25),
                (0.2, 0.35): ('normal', 15),
                (0, 0.2): ('bad', 5),
                (None, 0): ('error', 0)
            },
            'sleep_efficiency': {
                (1, None): ('error', 0),
                (0.8, 1): ('good', 15),
                (0.6, 0.8): ('normal', 10),
                (0, 0.6): ('bad', 5),
                (None, 0): ('error', 0)
            }
        }

    def get_assess_level(self, title, input_value):
        for key, value in self.assess_level[title].iteritems():
            if (key[0] is None):
                if input_value < key[1]:
                    return value
            elif (key[1] is None):
                if input_value >= key[0]:
                    return value
            elif key[0] <= input_value < key[1]:
                return value

    # 时间均以分钟记录     获取date天的评分和评价。
    def get_sleep_assess(self, off_bed_times, first_light_time, awake_time, light_time, deep_time):
        # moving_score 为浮动得分
        moving_score = 10

        (off_bed_times_level, off_bed_times_score) = self.get_assess_level('offbed', off_bed_times)
        off_bed_times_eval = self.assess_text['off_bed_times'][off_bed_times_level]

        (first_light_time_level, first_light_time_score) = \
            self.get_assess_level('first_light_time', first_light_time)
        first_light_time_eval = \
            self.assess_text['first_light_time'][first_light_time_level].format(
                first_light_time_minute=first_light_time)

        sleep_time = light_time + deep_time
        record_time = light_time + deep_time + awake_time

        (sleep_time_level, sleep_time_score) = self.get_assess_level('sleep_time', sleep_time)
        sleep_time_eval = self.assess_text['sleep_time'][sleep_time_level].format(
            sleep_time_hour=round(sleep_time * 1.0 / 60, 2))

        # 排除睡眠时间是0的情况
        if sleep_time > 0:
            deep_sleep_account = round(deep_time * 1.0 / sleep_time, 2)
        else:
            deep_sleep_account = 0

        (deep_sleep_account_level, deep_sleep_score) = \
            self.get_assess_level('deep_sleep_account', deep_sleep_account)
        deep_sleep_eval = self.assess_text['deep_sleep_account'][deep_sleep_account_level].format(
            deep_time_hour=round(deep_time * 1.0 / 60, 2),
            deep_sleep_percet=int(deep_sleep_account * 100))

        # 排除记录时间是0的情况
        if record_time > 0:
            sleep_efficiency = round(sleep_time * 1.0 / record_time, 2)
        else:
            sleep_efficiency = 0

        (sleep_efficiency_level, sleep_efficiency_score) = \
            self.get_assess_level('sleep_efficiency', sleep_efficiency)

        score = sleep_time_score + sleep_efficiency_score + first_light_time_score + \
                deep_sleep_score + off_bed_times_score + moving_score

        score_level = self.get_assess_level('score', score)
        sleep_score_eval = self.assess_text['score'][score_level].format(total=score)

        sleepEval = [
            sleep_score_eval, sleep_time_eval,
            first_light_time_eval, deep_sleep_eval, off_bed_times_eval]

        return score, sleepEval

    # 获取日报数据
    def get_sleep_stat(self,resp, user_id, date):
        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAT_ALGORI_VERSION:
            self.analyser.analyse(user_id, date)  # analysis 计算date天的睡眠状态数据 和分析数据
            data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        sleep_stat = data_from_db.get('data')
        if sleep_stat is None or sleep_stat['validity'] is False:
            resp.body = json.dumps({'validity': False, 'score': 0})
            resp.status = falcon.HTTP_200
            return
        sleep_stat['validity'] = True
        # 将秒换算为分钟
        sleep_stat['awake'] = sleep_stat['awake'] / 60
        sleep_stat['light'] = sleep_stat['light'] / 60
        sleep_stat['deep'] = sleep_stat['deep'] / 60
        record_time = sleep_stat['awake'] + sleep_stat['light'] + sleep_stat['deep']

        if record_time < 3 * 60:
            sleep_stat['validity'] = False
            resp.body = json.dumps({'validity': False, 'score': 0})
            resp.status = falcon.HTTP_200
            return

        if sleep_stat.get('firstAwakeLight') is not None:
            sleep_stat['firstAwakeLight'] = sleep_stat['firstAwakeLight'] / 60
            sleep_stat['score'], sleep_stat['sleepEval'] = self.get_sleep_assess(
                sleep_stat['offbed'],
                sleep_stat['firstAwakeLight'],
                sleep_stat['awake'],
                sleep_stat['light'],
                sleep_stat['deep'])
        else:
            sleep_stat['score'] = None
            sleep_stat['sleepEval'] = ['数据无效,无法进行评价']
        if sleep_stat['duration']:
            sleep_stat['duration'][0] = str(sleep_stat['duration'][0])
            sleep_stat['duration'][1] = str(sleep_stat['duration'][1])
        return sleep_stat

    def on_get(self, req, resp, user_id, date):
        self.date = date
        self.user_id = user_id
        sleep_stat = self.get_sleep_stat(resp, user_id, date)
        resp.body = json.dumps(sleep_stat)
        resp.status = falcon.HTTP_200
