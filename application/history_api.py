# -*- coding: utf-8 -*-
import falcon
import json

import analyser
import dbutil


class History:

    def __init__(self, db):
        self.analyser = analyser.Analyser(db)
        self.db = db

    def on_get(self, req, resp, user_id, date):
        cursor, begin_interpolate = dbutil.get_source_data(self.db, user_id, date)  # cursor 为对应的
        many = []
        result = {'result': many}
        # 将history的数据中的_id的字段进行转化
        if begin_interpolate:
            begin_interpolate['time'] = begin_interpolate['_id'].isoformat()
            del begin_interpolate['_id']
            many.append(begin_interpolate)
        for item in cursor:
            item['time'] = item['_id'].isoformat()
            del item['_id']
            many.append(item)

        print(result)
        resp.body = json.dumps(result)
        resp.status = falcon.HTTP_200
