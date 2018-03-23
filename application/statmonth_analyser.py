# -*- coding: utf-8 -*-
from stage_analyser import StageAnalyser
import arith
import numpy
from analyser import Analyser
from application.analysis.stage_regularity_analyser import StageRegularityAnalyser
import datetime


class StatMonthAnalyser:
    def __init__(self, db):
        self.db = db
        self.stage_analyser = StageAnalyser()
        self.analyser = Analyser(self.db)
        self.stage_regularity_analyser = StageRegularityAnalyser(self.db)
        self.time_array = []  # 设置分隔为30分钟的时间段判定
        self.dict_time_point = {}  # 设置以时间段为key的记录时间点次数的dict
        self.offbed_time_array = []  # 所有睡眠期间离床时间集合
        self.divide_time()

    # 将时间进行分隔,为选择时间段做准备
    def divide_time(self):
        """
        分隔时间段，为确定离床集中的时间点设置assembly
        :return:  时间段array
        """
        start_time = '1900-01-01 00:00:00'
        start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_time = '1900-01-01 23:59:59'
        end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        self.time_array = []
        self.time_array.append(start_time)

        while True:
            if start_time >= end_time:
                break
            else:
                start_time += datetime.timedelta(hours=0.5)
                self.time_array.append(start_time)
        self.time_array.pop()  # 将第二天的0:00清除

    # 将得到的每天睡眠的时间中的非零的进行舍弃
    def get_valid_values(self, values):
        values_temp = []
        for temp in values:
            if temp != 0:
                values_temp.append(temp)
        return values_temp

    # 获取每日的离床时间
    def get_offbed_time(self, user_id, date):
        """
        通过睡眠状态接口的生成逻辑（暂认为睡眠状态所检测的时间段为真实的有效睡眠时间段），获取睡眠期间的离床时间段。
        :param user_id:用户Id
        :param date:日期
        :return:睡眠时间段的list[dict {offbed_time: time,offbed_range:timeRange}]
        """
        #  异常数据  2017-12-16  完成后查看。
        offbed_time = {}
        offbed_times = []
        # datestr = '2017-12-03'
        data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAGE_ALGORI_VERSION:  # 判断是否是读取数据库缓存还是直接进行计算。
            self.analyser.analyse(user_id, date)  # analyser 进行分析，然后就分析的数据写入到数据库中去
            data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        sleep_stages = data_from_db.get('data', [])

        for i in range(len(sleep_stages) - 1):  # 把最后面的offbed数据进行抹除
            # 判断离床是否是睡后离床还是正常离床；需要统计的是睡后离床
            if sleep_stages[i]['state'] == 'offbed' and 'afterSleep' in sleep_stages[i].keys():
                offbed_time['offbed_time'] = sleep_stages[i]['time']
                offbed_time['offbed_range'] = (sleep_stages[i + 1]['time'] - sleep_stages[i]['time']).seconds
                offbed_times.append(offbed_time.copy())
        return offbed_times

    # 获取平均离床时间段、最长离床时间
    def get_aver_large_offbed_time(self, offbed_times):
        """
        获取平均离床时间段、最长离床时间
        :param offbed_times:
        :return:   {aver_offbed_time:value,large_offbed_time:value}
        """
        sum_offbed_times = 0
        count = 0
        large_offbed_time = 0
        for item in offbed_times:
            max_current_offbed_time = 0
            for item_offbed in item:
                self.offbed_time_array.append(item_offbed['offbed_range'])
                sum_offbed_times += item_offbed['offbed_range']
                max_current_offbed_time += item_offbed['offbed_range']
                count += 1

            if large_offbed_time < max_current_offbed_time:
                large_offbed_time = max_current_offbed_time

        aver_offbed_time = round((sum_offbed_times * 1.0) / (count * 1.0), 4)
        dict_aver_large_offbed_time = {'aver_offbed_time': aver_offbed_time, 'large_offbed_time': large_offbed_time}
        return dict_aver_large_offbed_time

    def get_offbed_time_point(self, offbed_times):
        """
        获取离床主要集中的时间段（此处离床为睡眠期间离床，而非日常离床）
        离床主要集中的时间段计算方式：  算出平均离床时间段、标准差，算出离床范围；
        根据离床范围确定离床集中的时间点；（选择根据离床范围作为过滤原因 ： 默认不在离床范围内的数据为可用性低的数据）
        时间点进行模糊处理，interval 为30 minutes；时间匹配方式为向前匹配
        :param offbed_times:  一个月的睡眠时间段的离床时间
        :return:  []
        """
        for i in range(len(self.time_array)):
            key = self.time_array[i].strftime('%Y-%m-%d %H:%M:%S')  # 时间point作为key
            self.dict_time_point[key] = 0

        dict_aver_large_offbed_time = self.get_aver_large_offbed_time(offbed_times)
        aver_offbed_time = dict_aver_large_offbed_time['aver_offbed_time']

        offbed_time_std = numpy.std(
            self.get_valid_values(self.offbed_time_array), ddof=0)
        # 由于样本容量较小，故用有偏标准差进行计算。
        offbed_time_range = [0] * int(2)  # 声明 score list的大小
        if offbed_time_range:  # 获取离床时间范围
            offbed_time_range[0] = str(aver_offbed_time - offbed_time_std)  # 单位为 s
            offbed_time_range[1] = str(aver_offbed_time + offbed_time_std)
        for item in offbed_times:
            for item_offbed in item:
                if float(offbed_time_range[0]) <= item_offbed['offbed_range'] and float(item_offbed['offbed_range']) <= \
                        offbed_time_range[1]:
                    get_time = item_offbed['offbed_time']  # datetime.datetime.strptime(, '%Y-%m-%d %H:%M:%S.%Z')
                    for i in range(len(self.time_array) - 1):
                        if get_time.hour == self.time_array[i].hour:
                            if get_time.minute >= self.time_array[i].minute and get_time.minute < self.time_array[
                                i + 1].minute:
                                key = self.time_array[i].strftime('%Y-%m-%d %H:%M:%S')  # 时间point作为key
                                self.dict_time_point[key] += 1
                                break

        if len(self.dict_time_point) >= arith.MONTH_OFFBED_POINT_TIMES:
            keys = sorted(self.dict_time_point, key=lambda x: self.dict_time_point[x], reverse=True)[
                   0:arith.MONTH_OFFBED_POINT_TIMES]
        else:
            keys = sorted(self.dict_time_point, key=lambda x: self.dict_time_point[x], reverse=True)[
                   0:len(self.dict_time_point)]

        result_final = {'offbed_time_range': offbed_time_range}  # 夜间平均离床时间范围
        result = {}  # 睡眠期间离床前三多时间段及对应次数
        # 时间点前的默认的date数据清除
        for i in range(len(keys)):
            result[keys[i]] = self.dict_time_point[keys[i]]
            date_temp = datetime.datetime.strptime(keys[i], '%Y-%m-%d %H:%M:%S')  # str transform to datetimea
            time_temp = datetime.time(date_temp.hour, date_temp.minute, date_temp.second)
            result[time_temp.strftime('%H:%M:%S')] = result.pop(keys[i])
        result_final['offbed_time_point'] = result
        result_final['offbed_time_std'] = offbed_time_std
        return result_final

    # 判断月作息规律性
    def calc_sleep_month_regularity(self, user_id, date):
        pass
