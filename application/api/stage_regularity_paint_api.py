# -*- coding: utf-8 -*-
import falcon
import json
from application.analyser import Analyser
from application.analysis.stage_regularity_analyser import StageRegularityAnalyser


class StageRegularityPaintApi:

    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.stage_regularity_analyser = StageRegularityAnalyser(self.db)

    def on_get(self, req, resp, user_id, date):
        """
              暂时不将作息规律性写入数据库中
        # data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        #  if data_from_db is None or data_from_db['ver'] != application.arith.SLEEP_STAGE_ALGORI_VERSION:
        #     判断是否是读取数据库缓存还是直接进行计算。
        #     self.analyser.analyse(user_id, date)  # analyser 进行分析，然后就分析的数据写入到数据库中去
        #     data_from_db = self.db.sleep_phase[user_id].find_one({'_id': date})
        # sleep_stages = data_from_db.get('data', [])
        """
        # 得到6:00-6:00 of the next day
        sleep_stages = self.stage_regularity_analyser.calc_sleep_regularity(user_id, date)
        sleep_stages_result = self.stage_regularity_analyser.translate_sleep_stages(sleep_stages)
        for item in sleep_stages_result:
            item['time'] = item['time'].isoformat()
            # print(item['time'] + "    " + item['state'])
        result = {'result': sleep_stages_result}
        resp.body = json.dumps(result)
        resp.status = falcon.HTTP_200
