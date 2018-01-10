# -*- coding: utf-8 -*-
from pymongo import MongoClient
from gevent import pywsgi
import falcon
from datetime import datetime

import settings
from stage_api import Stages
from statistics_api import Statistics
from history_api import History
from nursing_api import NursingAnalyser
from statisticsForMonth_api import StatisticsForMonth


def start():
    app = falcon.API(middleware=[])
    db = MongoClient(
        'mongodb://%s:%s@%s:%s' % (
            settings.config['db']['user'],
            settings.config['db']['password'],
            settings.config['db']['host'],
            settings.config['db']['port']))
    app.add_route('/analyser/reports/{user_id}/{date}', Stages(db))
    app.add_route('/analyser/statistics/{user_id}/{date}', Statistics(db))
    app.add_route('/analyser/statisticsForMonth/{user_id}/{date}', StatisticsForMonth(db))
    app.add_route('/analyser/history/{user_id}/{date}', History(db))
    app.add_route('/analyser/nursing/{user_id}/{date}', NursingAnalyser(db))
    print(datetime.now(), 'Report service started on port', settings.config['rest_api_port'])
    pywsgi.WSGIServer(('', settings.config['rest_api_port']), app).serve_forever()
