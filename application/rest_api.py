# -*- coding: utf-8 -*-
from pymongo import MongoClient
from gevent import pywsgi
import falcon
from datetime import datetime

import settings
from application.api.stage_health_score_api import StageHealthScoreApi
from application.api.stagemonth_sleep_efficiency_api import StageMonthSleepEfficiencyApi
from application.api.stage_regularity_score_api import StageRegularityScoreApi
from stage_api import Stages
from statistics_api import Statistics
from history_api import History
from nursing_api import NursingAnalyser
from statisticsForMonth_api import StatisticsForMonth
from application.api.stage_regularity_paint_api import StageRegularityPaintApi
from application.algorithm.naive_bayes_score_reasonable_api import MultinomialNBScoreReasonable


def start():
    app = falcon.API(middleware=[])
    db = MongoClient(
        'mongodb://%s:%s@%s:%s' % (
            settings.config['db']['user'],
            settings.config['db']['password'],
            settings.config['db']['host'],
            settings.config['db']['port']))
    app.add_route('/analyser/sleepStatus/{user_id}/{date}', Stages(db))
    app.add_route('/analyser/statistics/{user_id}/{date}', Statistics(db))
    app.add_route('/analyser/history/{user_id}/{date}', History(db))
    app.add_route('/analyser/nursing/{user_id}/{date}', NursingAnalyser(db))

    app.add_route('/analyser/statisticsForMonth/{user_id}/{date}', StatisticsForMonth(db))  # 月报汇总接口
    app.add_route('/analyser/stageRegularityPaintApi/{user_id}/{date}', StageRegularityPaintApi(db))  # 日作息规律性绘图接口
    app.add_route('/analyser/stageMonthSleepEfficiencyApi/{user_id}/{date}',
                  StageMonthSleepEfficiencyApi(db))  # 月报睡眠效率概况接口
    app.add_route('/analyser/StageRegularityScoreApi/{user_id}/{date}', StageRegularityScoreApi(db))  # 日作息规律性得分接口
    app.add_route('/analyser/StageHealthScoreApi/{user_id}/{date}', StageHealthScoreApi(db))  # 日健康评分接口
    app.add_route('/algorithm/MultinomialNBScoreReasonable/{user_id}/{date}', MultinomialNBScoreReasonable(db))  # 预测日得分接口

    # 测试接口
    print(datetime.now(), 'Report service started on port', settings.config['rest_api_port'])
    pywsgi.WSGIServer(('', settings.config['rest_api_port']), app).serve_forever()
