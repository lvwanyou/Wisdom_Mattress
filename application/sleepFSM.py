# -*- coding: utf-8 -*-

from transitions import Machine
import arith

"""
transitions是一个由Python实现的轻量级的、面向对象的有限状态机框架。
transitions最基本的用法如下，先自定义一个类，然后定义一系列状态和状态转移（定义状态和状态转移有多种方式，下面只写了最简明的一种，具体要参考文档说明），
最后初始化状态机。
"""


class SleepStateMachine(object):
    states = [
        {'name': 'offline', 'on_enter': 'on_enter_state'},
        {'name': 'offbed', 'on_enter': 'on_enter_offbed_state'},
        {'name': 'awake', 'on_enter': 'on_enter_state'},
        {'name': 'light', 'on_enter': 'on_enter_state'},
        {'name': 'deep', 'on_enter': 'on_enter_state'}
    ]

    transitions = [
        {'trigger': 'offline', 'source': '*', 'dest': 'offline'},

        {'trigger': 'offbed', 'source': '*', 'dest': 'offbed'},

        {'trigger': 'moving', 'source': 'offline', 'dest': 'awake'},
        {'trigger': 'moving', 'source': 'offbed', 'dest': 'awake'},
        {'trigger': 'moving', 'source': 'awake', 'dest': 'awake'},
        {'trigger': 'moving', 'source': 'light', 'dest': 'awake', 'conditions': 'can_light_to_awake'},
        {'trigger': 'moving', 'source': 'deep', 'dest': 'light', 'conditions': 'can_deep_to_light'},

        {'trigger': 'normal', 'source': 'offline', 'dest': 'awake'},
        {'trigger': 'normal', 'source': 'offbed', 'dest': 'awake'},
        {'trigger': 'normal', 'source': 'awake', 'dest': 'light', 'conditions': 'can_awake_to_light'},
        {'trigger': 'normal', 'source': 'light', 'dest': 'deep', 'conditions': 'can_light_to_deep'},
        {'trigger': 'normal', 'source': 'deep', 'dest': 'deep'}
    ]

    def __init__(self):
        self.moves_since_enter_state = 0
        # self.moves_count_since_enter_state = 0
        self.onbed_time = None
        self.machine = Machine(
            model=self,
            states=SleepStateMachine.states,
            transitions=self.transitions,
            initial='offline')

    def trigger(self, event, mat_data):
        func = getattr(self, event, None)
        if func and callable(func):
            func(mat_data=mat_data)
        return self.state

    def on_enter_offbed_state(self, mat_data):
        self.onbed_time = None
        self.on_enter_state(mat_data)

    def on_enter_state(self, mat_data):
        self.state_enter_time = mat_data['time']
        self.moves_since_enter_state = 0
        # self.moves_count_since_enter_state = 0

    def can_light_to_awake(self, mat_data):
        """ 浅睡状态，连续翻身N次进入清醒状态. """
        self.moves_since_enter_state += 1
        arith_param_type = arith.DEV_MODEL_TO_ARITH_TYPE[mat_data.get('model')]
        if self.moves_since_enter_state >= \
                arith.SLEEP_PARAMETER[arith_param_type]['MOVES_LIGHT_TO_AWAKE']:
            return True
        else:
            return False

    def can_deep_to_light(self, mat_data):
        """ 深睡状态，连续翻身N次进入浅睡状态. """

        self.moves_since_enter_state += 1
        arith_param_type = arith.DEV_MODEL_TO_ARITH_TYPE[mat_data.get('model')]
        if self.moves_since_enter_state >= \
                arith.SLEEP_PARAMETER[arith_param_type]['MOVES_DEEP_TO_LIGHT']:
            return True
        else:
            return False

    def can_awake_to_light(self, mat_data):
        """ 清醒状态，连续静卧N分钟进入浅睡状态. """
        arith_param_type = arith.DEV_MODEL_TO_ARITH_TYPE[mat_data.get('model')]
        if (mat_data['time'] - self.state_enter_time).seconds >= \
                arith.SLEEP_PARAMETER[arith_param_type]['TIME_AWAKE_TO_LIGHT']:
            return True
        else:
            return False

    def can_light_to_deep(self, mat_data):
        """ 浅睡状态，连续静卧N分钟进入深睡状态. """
        arith_param_type = arith.DEV_MODEL_TO_ARITH_TYPE[mat_data.get('model')]
        if (mat_data['time'] - self.state_enter_time).seconds >= \
                arith.SLEEP_PARAMETER[arith_param_type]['TIME_LIGHT_TO_DEEP']:
            return True
        else:
            return False
