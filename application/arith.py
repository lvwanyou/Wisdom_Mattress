# -*- coding: utf-8 -*-

"""
睡眠相关的算法或参数有改动，相应的版本号需要加1，并增加备注
    2 - 第一个基础版本
    3 - 解决掉线问题，掉线跟离床一样处理
    4 - 解决睡眠时间区间过长问题
    5 - 修改睡眠区间以及区间计算方法
    6 - 增加参数TIME_OFFBED_TO_AWAKE，减少无效离床次数
    7 - bugfix：睡眠分段不是以offbed开始会导致第一段睡眠不统计
    8 - 根据设备不同，使用不同的分期参数，默认参数为htjr 增加过滤短时间碎片化的睡眠阶段
    9 - 去除晚上六点之前的不合理的睡眠部分，增加参数HOURS_BESIDE_SLEEP_SECTION
    10 - 优化离床次数，新增一个睡眠后离床的表示
    11 - bugfix: 计算平均心率、呼吸率，没有去除掉线的部分
    12 - 状态机去掉offbed到awake的短时间在床的过滤，因为新增了间歇性离床
    13 - SLEEP_MAX_GAP 修改为30
"""
# 睡眠阶段算法
SLEEP_STAGE_ALGORI_VERSION = 13

"""
睡眠相关的算法或参数有改动，相应的版本号需要加1，并增加备注
    8 - 睡眠评分更新算法，增加参数firstAwakeLight，增加评价
    9 - 睡眠评分各评价参数均增加一个级别，解决darama 大医 与实际差异过大
    10 - 睡眠阶段算法更新为8
    11 - 睡眠阶段算法更新为9
    12 - 睡眠统计存储结构修改
    13 - 睡眠阶段算法更新为11
    14 - 睡眠阶段算法更新为12
    15 - 睡眠阶段算法更新为13
"""
# 睡眠评分算法版本，如果睡眠阶段算法有升级，则该算法版本也须升级
SLEEP_STAT_ALGORI_VERSION = 15

# 睡眠阶段相关参数
SLEEP_MAX_GAP = 30   # （分钟）合理区间之外的部分，超出该间隔的不计入有效睡眠
MIN_SLEEP_TIME = 10  # （分钟）最短的睡眠时间，小于该值不认为是睡眠
SLEEP_SECTION = [20, 6]  # 晚间睡眠的合理区间
MIN_SLEEP_STAGE_TIME = 5  # （分钟）最短的睡眠阶段，小于该值不认为是一个睡眠阶段（过滤碎片化的睡眠阶段）
HOURS_BESIDE_SLEEP_SECTION = 2  # 合理睡眠区间之外可能计算进入睡眠的部分，前提是满足SLEEP_MAX_GAP

# 睡眠状态机相关参数
SLEEP_PARAMETER = {
    'htjr': {
        'MOVES_LIGHT_TO_AWAKE': 25,     # 浅睡状态，连续翻身多少次，进入清醒状态
        'MOVES_DEEP_TO_LIGHT': 3,       # 深睡状态，连续翻身多少次，进入浅睡状态
        'TIME_AWAKE_TO_LIGHT': 600,     # 清醒状态，连续多少秒静卧，进入浅睡状态
        'TIME_LIGHT_TO_DEEP': 1080      # 浅睡状态，连续多少秒静卧，进入深睡状态
    },
    'darma': {
        'MOVES_LIGHT_TO_AWAKE': 30,     # 浅睡状态，连续翻身多少次，进入清醒状态
        'MOVES_DEEP_TO_LIGHT': 5,       # 深睡状态，连续翻身多少次，进入浅睡状态
        'TIME_AWAKE_TO_LIGHT': 200,     # 清醒状态，连续多少秒静卧，进入浅睡状态
        'TIME_LIGHT_TO_DEEP': 350       # 浅睡状态，连续多少秒静卧，进入深睡状态
    }
}

TIME_OFFBED_TO_AWAKE = 120  # 离床状态，连续多少秒在床，进入清醒状态，该参数用以减少无效离床次数


DEV_MODEL_TO_ARITH_TYPE = {
    'htjr': 'htjr',
    'darma': 'darma',
    'murata': 'htjr',
    'None': 'htjr'
}
