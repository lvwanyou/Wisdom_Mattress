# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil import parser

from stage_analyser import StageAnalyser
import arith
import dbutil


class StatMonthAnalyser:

    def __init__(self, db):
        self.db = db
        self.stage_analyser = StageAnalyser()

    # 将得到的每天睡眠的时间中的非零的进行舍弃
    def get_valid_sleep_times(self, sleep_times):
        sleep_times_temp = []
        for temp in sleep_times:
            if temp != 0:
                sleep_times_temp.append(temp)
        return sleep_times_temp
