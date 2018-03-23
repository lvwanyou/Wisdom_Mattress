# -*- coding: utf-8 -*-
import falcon
import json
from application.analyser import Analyser
from application.analysis.stage_regularity_analyser import StageRegularityAnalyser


class StageRegularityScoreApi:

    def __init__(self, db):
        self.db = db
        self.analyser = Analyser(self.db)
        self.stage_regularity_analyser = StageRegularityAnalyser(self.db)

    def on_get(self, req, resp, user_id, date):
        """
          获取日作息规律性得分
        """
        total_score = 100  # 设置日作息规律性得分满分
        # 得到6:00-6:00 of the next day   日作息规律性原始数据
        sleep_stages = self.stage_regularity_analyser.calc_sleep_regularity(user_id, date)
        sleep_stages_result = self.stage_regularity_analyser.translate_sleep_stages(sleep_stages)
        # 根据原始数据及作息规律表的比对进行打分，获取得分
        daily_regularity_score, sleep_stages_score = self.stage_regularity_analyser.get_daily_regularity_score(
            sleep_stages_result,
            date, total_score)
        result = {
            'daily_regularity_score': daily_regularity_score,
            'sleep_stages_score': sleep_stages_score
        }
        resp.body = json.dumps(result)
        resp.status = falcon.HTTP_200
