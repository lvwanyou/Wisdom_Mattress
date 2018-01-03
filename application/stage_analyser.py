# -*- coding: utf-8 -*-
import sleepFSM


class StageAnalyser(object):
    def __init__(self):
        super(StageAnalyser, self).__init__()
        self.init()

    def init(self):
        self.last_mat_data = {}
        self.last_sleep_stage = {}
        self.sleep_stages = []
        self.sleep_stage_machine = sleepFSM.SleepStateMachine()  # 引用睡眠状态Finite State Machine
        self.measure = {
            'heartbeat': {'total': 0, 'times': 0},
            'breath': {'total': 0, 'times': 0},
        }
        self.statistic = {
            'heartbeat': 0,  # 平均值
            'breath': 0,  # 平均值
            'offbed': 0,  # 离床次数
            'offline': 0,  # 掉线次数
            'firstAwakeLight': 0,  # 潜伏期
            'awake': 0,  # 清醒时间（s）
            'light': 0,  # 轻度睡眠时间（s）
            'deep': 0  # 深度睡眠时间（s）
        }

    def get_sleep_stage(self):
        return self.sleep_stages

    def get_sleep_statistic(self):
        if self.measure['heartbeat']['times'] > 0:
            self.statistic['heartbeat'] = (
                    self.measure['heartbeat']['total'] / self.measure['heartbeat']['times'])
        if self.measure['breath']['times'] > 0:
            self.statistic['breath'] = (
                    self.measure['breath']['total'] / self.measure['breath']['times'])
        return self.statistic

    # 将数据记录到measure中去，为statistic 数据的更新做准备
    def update_body_statistic(self, mat_data):
        if mat_data['state'] == 'offbed' or mat_data['state'] == 'offline':
            return
        if type(mat_data['heartbeat']) != int or type(mat_data['breath']) != int:
            print 'illegal mat data', mat_data
            return
        self.measure['heartbeat']['total'] += int(mat_data['heartbeat'])
        self.measure['heartbeat']['times'] += 1
        self.measure['breath']['total'] += int(mat_data['breath'])
        self.measure['breath']['times'] += 1

    # 根据new_sleep_stage和last_sleep_stage 来判断last_sleep_stage 持续的状态。
    def save_sleep_statistic(self, last_sleep_stage, new_sleep_stage):
        delta_time = new_sleep_stage['time'] - last_sleep_stage['time']
        if last_sleep_stage['state'] in {'offbed', 'offline'}:
            self.statistic[last_sleep_stage['state']] += 1  # 离床离线只记录次数
        else:
            self.statistic[last_sleep_stage['state']] += (
                    delta_time.days * 24 * 3600 + delta_time.seconds)

    def save_sleep_stage(self, sleep_stage):
        self.sleep_stages.append(sleep_stage)

    def init_sleep_stage(self, mat_data):
        init_state = self.sleep_stage_machine.trigger(
            mat_data['state'], mat_data)  # 根据state的原始状态分析判断睡眠的状态是  awake;deep;light;off_bed
        self.last_sleep_stage = {
            'state': init_state, 'time': mat_data['time']}
        self.save_sleep_stage(self.last_sleep_stage.copy())

    # 利用init_sleep_stage判断睡眠的状态是  awake;deep;light;off_bed  ,同时将数据存入到sleep_stages list中去
    def update_sleep_stage(self, mat_data):
        if self.last_sleep_stage == {}:
            self.init_sleep_stage(mat_data)
            return

        new_state = self.sleep_stage_machine.trigger(
            mat_data['state'], mat_data)
        if new_state != self.last_sleep_stage['state']:
            new_sleep_stage = {
                'state': new_state, 'time': mat_data['time']}
            self.save_sleep_statistic(self.last_sleep_stage, new_sleep_stage)
            self.save_sleep_stage(new_sleep_stage)
            self.last_sleep_stage.update(new_sleep_stage)
            return new_sleep_stage

    def mat_data_changed(self, mat_data):
        if self.last_mat_data.get('state') != mat_data.get('state') or \
                self.last_mat_data.get('heartbeat') != mat_data.get('heartbeat') or \
                self.last_mat_data.get('breath') != mat_data.get('breath') or \
                self.last_mat_data.get('pos') != mat_data.get('pos'):
            return True
        else:
            return False

    def process(self, mat_data):  #
        if self.last_mat_data == {}:
            self.last_mat_data.update(mat_data)
        self.update_body_statistic(mat_data)  # 将数据记录到measure中去，为statistic 数据的更新做准备
        self.update_sleep_stage(mat_data)    #  利用init_sleep_stage判断睡眠的状态是  awake;deep;light;off_bed  ,同时将数据存入到sleep_stages list中去
        self.last_mat_data.update(mat_data)
