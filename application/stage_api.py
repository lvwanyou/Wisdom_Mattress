# -*- coding: utf-8 -*-
import falcon
import json

from analyser import Analyser
import arith


class Stages:

    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)

    def on_get(self, req, resp, user_id, date):
        data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        if data_from_db is None or data_from_db['ver'] != arith.SLEEP_STAGE_ALGORI_VERSION:  # 判断是否是读取数据库缓存还是直接进行计算。
            self.analyser.analyse(user_id, date)  # analyser 进行分析，然后就分析的数据写入到数据库中去
            data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        sleep_stages = data_from_db.get('data', [])
        for item in sleep_stages:
            item['time'] = item['time'].isoformat()
        #   get the status of sleep;time range from date 20.00  to
        result = {'result': sleep_stages}
        resp.body = json.dumps(result)
        resp.status = falcon.HTTP_200
