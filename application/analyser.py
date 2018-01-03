# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil import parser

from stage_analyser import StageAnalyser
import arith
import dbutil


class Analyser:

    def __init__(self, db):
        self.db = db
        self.stage_analyser = StageAnalyser()

    def analyse_source_data(self, cursor):
        self.stage_analyser.init()
        last_mat_data = None
        for item in cursor:
            item['time'] = item['_id']
            sn = item['sn']
            if len(sn) == 6:
                item['model'] = 'htjr'
            elif len(sn) == 12:
                item['model'] = 'darma'
            else:
                item['model'] = 'murata'
            if last_mat_data is None:
                last_mat_data = item.copy()
            # 数据库中存储的是经过过滤的原始数据，需要恢复成每三秒一次的原始数据再分析
            # 时间戳的间距不是严格的三秒的整数倍，一般比三秒略大几毫秒
            if (item['time'] - last_mat_data['time']).seconds > 5:
                while (item['time'] - last_mat_data['time']).seconds > 4:
                    last_mat_data['time'] += timedelta(0, 3)
                    self.stage_analyser.process(mat_data=last_mat_data)
            self.stage_analyser.process(mat_data=item)
            last_mat_data = item.copy()

    def get_sleep_stage(self):
        return self.stage_analyser.get_sleep_stage()

    def get_sleep_statistic(self):
        return self.stage_analyser.get_sleep_statistic()

    def get_sleep_start(self, sleep_stage):
        if ((sleep_stage[0]['state'] == 'offbed' or sleep_stage[0]['state'] == 'offline') and
                sleep_stage[1]['state'] == 'awake' and
                sleep_stage[2]['state'] == 'light'):
            return sleep_stage[2]['time']

    # 从一天数据根据sleep_stage变化找出实际睡眠时间段
    def get_sleep_series(self, sleep_stage):
        stage_num = len(sleep_stage)
        sleep_time = []  # 睡眠时间段列表
        a_sleep_duration = {}

        for i in xrange(stage_num):
            if a_sleep_duration.get('sleep_begin_time') is None:
                if sleep_stage[i]['state'] == 'awake':
                    a_sleep_duration['sleep_begin_time'] = sleep_stage[i]['time']
                else:
                    continue
            elif a_sleep_duration.get('sleep_end_time') is None:
                if (sleep_stage[i]['state'] == 'offbed' or
                        sleep_stage[i]['state'] == 'offline' or
                        i == stage_num - 1):
                    a_sleep_duration['sleep_end_time'] = sleep_stage[i]['time']

            if a_sleep_duration.get('sleep_begin_time') and a_sleep_duration.get('sleep_end_time'):
                a_sleep_duration['sleep_duration'] = \
                    (a_sleep_duration['sleep_end_time'] -
                     a_sleep_duration['sleep_begin_time']).total_seconds()
                sleep_time.append(a_sleep_duration.copy())
                a_sleep_duration = {}
        return sleep_time
        # 过滤非睡眠的短时间段
        # new_sleep_time = []
        # for i in xrange(len(sleep_time)):
        #     if sleep_time[i]['sleep_duration'] >= arith.MIN_SLEEP_TIME * 60:
        #         new_sleep_time.append(sleep_time[i])
        # return new_sleep_time

    def get_sleep_interval(self, date, sleep_stages):
        sleep_series = self.get_sleep_series(sleep_stages)
        sleep_series_num = len(sleep_series)
        if sleep_series_num == 0:
            return None

        begin_of_sleep_day = parser.parse(date)
        begin_timestamp = begin_of_sleep_day + timedelta(hours=arith.SLEEP_SECTION[0])
        end_timestamp = begin_of_sleep_day + timedelta(hours=24 + arith.SLEEP_SECTION[1])

        sleep_start_index = None
        for i in xrange(sleep_series_num):
            if sleep_series[i]['sleep_end_time'] > begin_timestamp:
                sleep_start_index = i
                break
        if sleep_start_index is None:
            return None

        sleep_end_index = sleep_series_num - 1
        for i in xrange(sleep_start_index, sleep_series_num):
            if (sleep_series[i]['sleep_begin_time'] < end_timestamp and
                    sleep_series[i]['sleep_end_time'] > end_timestamp):
                sleep_end_index = i
                break
            elif (sleep_series[i]['sleep_begin_time'] > end_timestamp and
                  sleep_series[i]['sleep_end_time'] > end_timestamp):
                sleep_end_index = i - 1
                break

        # 该时间段之外的睡眠，如果相邻间隔小于arith.SLEEP_MAX_GAP，也计入有效睡眠
        i = sleep_start_index
        while i > 0:
            if (begin_timestamp - sleep_series[i - 1]['sleep_end_time']).total_seconds() < 2 * 3600:
                gap = sleep_series[i]['sleep_begin_time'] - sleep_series[i - 1]['sleep_end_time']
                if (gap.total_seconds() <= arith.SLEEP_MAX_GAP * 60):
                    sleep_start_index = i
                    i = i - 1
                    continue
            break

        i = sleep_end_index
        while i < sleep_series_num - 1:
            if (sleep_series[i + 1]['sleep_begin_time'] - end_timestamp).total_seconds() < 2 * 3600:
                gap = sleep_series[i + 1]['sleep_begin_time'] - sleep_series[i]['sleep_end_time']
                if (gap.total_seconds() <= arith.SLEEP_MAX_GAP * 60):
                    sleep_end_index = i
                    i = i + 1
                    continue
            break

        return [sleep_series[sleep_start_index]['sleep_begin_time'],
                sleep_series[sleep_end_index]['sleep_end_time']]

    # 根据最初数据来得到实际睡眠开始 结束时间
    def calc_sleep_report(self, user_id, date):
        cursor, _ = dbutil.get_source_data(self.db, user_id, date)
        self.analyse_source_data(cursor)
        sleep_stages = self.get_sleep_stage()
        sleep_duration = self.get_sleep_interval(date, sleep_stages)

        sleep_stat = {}
        if sleep_duration is None:
            sleep_stat['validity'] = False
            return sleep_stat, []
        else:
            sleep_stat['validity'] = True
            sleep_stat['duration'] = sleep_duration

        night_sleep_stages = filter(
            lambda x: sleep_duration[0] <= x['time'] <= sleep_duration[1],
            sleep_stages)
        sleep_stat['firstAwakeLight'] = self.get_first_awake_light(night_sleep_stages)
        sleep_stat['awake'] = 0
        sleep_stat['light'] = 0
        sleep_stat['deep'] = 0
        sleep_stat['offbed'] = 0
        sleep_stat['heartbeat'] = self.get_sleep_statistic()['heartbeat']
        sleep_stat['breath'] = self.get_sleep_statistic()['breath']

        for i in range(len(night_sleep_stages) - 1):
            try:
                if night_sleep_stages[i]['state'] in ('awake', 'light', 'deep'):
                    sleep_stat[night_sleep_stages[i]['state']] += (
                        (night_sleep_stages[i + 1]['time'] - night_sleep_stages[i]['time']).seconds)
                elif night_sleep_stages[i]['state'] == 'offbed':
                    # 标识睡眠期间的离床，只有进入了睡眠状态后的离床才认为是睡眠期间的离床
                    if night_sleep_stages[i - 1]['state'] in ('light', 'deep'):
                        sleep_stat['offbed'] += 1
                        night_sleep_stages[i]['afterSleep'] = True
                    elif night_sleep_stages[i - 1]['state'] == 'awake' and \
                            night_sleep_stages[i - 2]['state'] in ('light', 'deep'):
                        sleep_stat['offbed'] += 1
                        night_sleep_stages[i]['afterSleep'] = True
            except Exception:
                continue

        return sleep_stat, night_sleep_stages

    def get_sleep_duration(self, user_id, date):
        data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        # 第一次数据库若查询不到，则需计算，计算结果会自动缓存到数据库
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAT_ALGORI_VERSION:
            self.analyse(user_id, date)
            data_from_db = self.db.sleep_stat[user_id].find_one({'_id': date})
        data = data_from_db.get('data')
        if data is None or data['validity'] is False:
            return None

        return data_from_db['data']['duration']

    # 计算潜伏期
    def get_first_awake_light(self, sleep_stage):
        stage_num = len(sleep_stage)
        firstawake = None
        firstlight = None
        for i in xrange(stage_num - 1):
            if ((sleep_stage[i]['state'] == 'awake') and (sleep_stage[i + 1]['state'] == 'light')):
                firstawake = sleep_stage[i]['time']
                firstlight = sleep_stage[i + 1]['time']
                break
        if (firstlight is None) or (firstawake is None):
            return None

        firstAwakeLight = (firstlight - firstawake).seconds
        return firstAwakeLight

    # 滤出睡眠分期中的细碎阶段
    def remove_short_sleep_stage(self, sleep_stage):
        stage_num = len(sleep_stage)
        temp_sleep_stage = [sleep_stage[0]]
        for i in xrange(stage_num - 1):
            if (i and ((sleep_stage[i]['state'] == 'offbed') or
                       (sleep_stage[i]['state'] == 'offline') or
                       ((sleep_stage[i + 1]['time'] - sleep_stage[i]['time']).seconds >=
                        arith.MIN_SLEEP_STAGE_TIME * 60))):
                if not (temp_sleep_stage[-1]['state'] == sleep_stage[i]['state']):
                    temp_sleep_stage.append(sleep_stage[i])
        sleep_stage = temp_sleep_stage
        return sleep_stage

    # 计算出所有睡眠分析的结果，并缓存到数据库，当算法版本有变化时，由调用者触发重新计算
    def analyse(self, user_id, date):
        # calc_sleep_report()函数对sleep_statistic和sleep_stages 进行计算
        sleep_stat, sleep_stages = self.calc_sleep_report(user_id, date)
        # 1.在08:00之前查询，需要动态计算，缓存结果的版本号为0
        # 2.在08:00之后查询，缓存的版本号为正式算法版本号，下次再查询直接用缓存
        end_point = parser.parse(date) + timedelta(days=1, hours=8)
        time_gap = (datetime.now() - end_point)
        print(time_gap)
        if time_gap.days >= 0 and time_gap.seconds >= 0:
            sleep_stage_algori_ver = arith.SLEEP_STAGE_ALGORI_VERSION
            sleep_stat_algori_ver = arith.SLEEP_STAT_ALGORI_VERSION
        else:
            sleep_stage_algori_ver = 0
            sleep_stat_algori_ver = 0
        dbutil.save_sleep_stage(self.db, sleep_stage_algori_ver, user_id, date, sleep_stages)
        dbutil.save_sleep_stat(self.db, sleep_stat_algori_ver, user_id, date, sleep_stat)
