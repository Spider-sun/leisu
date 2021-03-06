from gevent import monkey
monkey.patch_all()

import requests
import re
import schedule
import time
import threading

from lxml import etree
from gevent.pool import Pool
from queue import Queue

from football.db.mongo_pool import MongoDB
from football.db.redis_pool import Redis_Pool
from IP_API.proxy import get_ip
from football.settings import HEADERS, TEST_EVENTS_INTERVAL, TEST_PROXIES_ASYNC_COUNT


"""
    数据分析内容
"""
class DataSpider(object):
    def __init__(self):
        self.redis = Redis_Pool()
        self.mongo_home_page = MongoDB('home_page')
        self.mongo = MongoDB('football_shujufenxi')

        # 创建队列和协程池
        self.queue = Queue()
        self.coroutine_pool = Pool()

    def __chech_callbake(self, temp):
        '''异步回调函数'''
        if not self.queue.empty():
            self.coroutine_pool.apply_async(self.__get_data, callback=self.__chech_callbake)

    def get_events_ID(self, name):
        datas = self.redis.find(name)
        for k, v in datas.items():
            msg = eval(k)
            self.queue.put(msg)
        for i in range(TEST_PROXIES_ASYNC_COUNT):
            if not self.queue.empty():
                self.coroutine_pool.apply_async(self.__get_data, callback=self.__chech_callbake)
            # 守护线程
        self.coroutine_pool.join()

    def __get_data(self):
        proxy = get_ip()
        if not self.queue.empty():
            events_ID = self.queue.get()
            # 分析页面
            try:
                try:
                    if proxy:
                        resp = requests.get('https://live.leisu.com/shujufenxi-' + str(events_ID), proxies={'https': 'https://'+proxy, 'http': 'http://'+proxy}, headers=HEADERS).text
                    else:
                        resp = requests.get('https://live.leisu.com/shujufenxi-' + str(events_ID), headers=HEADERS).text
                    # print(type(resp))
                    msg = {}
                    msg['赛事ID'] = events_ID
                    # 盘路走势
                    since_trend = self.__get_trend(resp)
                    msg['盘路走势'] = since_trend
                    # 伤停情况
                    situation = self.__get_situation(resp)
                    msg['伤停情况'] = situation
                    # 联赛积分
                    league_points = self.__get_league_points(resp)
                    msg['联赛积分'] = league_points
                    # 历史战绩
                    historical = self.__get_historical(resp)
                    msg['历史战绩'] = historical
                    # 近期战绩
                    recent = self.__get_recent(resp)
                    msg['近期战绩'] = recent
                    # 保存数据
                    # print(msg)
                    self.mongo.insert_one(msg, '赛事ID')
                    # 调度队列的tesk_done方法
                    self.queue.task_done()
                except requests.exceptions.SSLError:
                    # 如果报错，再将为访问到的数据加入队列
                    self.queue.put((events_ID))
            except requests.exceptions.ProxyError:
                # 如果报错，再将为访问到的数据加入队列
                self.queue.put((events_ID))

    def __get_historical(self, resp):
        dict_data = {'data': []}
        result_ = re.findall('<div id="historical"[\s\S]*?(<tr[\s\S]*?</td>)</tr></table>', resp)
        if not result_:
            dict_data = '暂无数据'
        else:
            result = result_[0]
            html = etree.HTML(result)
            datas = html.xpath('//tr')[1:]
            for data in datas:
                dic = {}
                # 赛事
                event_1 = data.xpath('./td[1]/a/text()')
                if event_1:
                    dic['赛事'] = event_1[0].strip()
                else:
                    dic['赛事'] = ''
                # 时间
                time_1 = data.xpath('./td[2]/text()')
                if time_1:
                    dic['时间'] = time_1[0].strip()
                else:
                    dic['时间'] = ''
                # 主场球队
                home_team_1 = data.xpath('./td[3]/a/span/text()')
                if home_team_1:
                    dic['主场球队'] = home_team_1[0].strip()
                else:
                    dic['主场球队'] = ''
                # 比分
                score = data.xpath('./td[4]/a/span/text()')
                if score:
                    dic['比分'] = score[0] + ':' + score[1]
                else:
                    dic['比分'] = ''
                # 客场球队
                away_team_1 = data.xpath('./td[5]/a/span/text()')
                if away_team_1:
                    dic['客场球队'] = away_team_1[0].strip()
                else:
                    dic['客场球队'] = ''
                # 半场
                half_score = data.xpath('./td[6]/text()')
                if half_score:
                    dic['半场'] = half_score[0].strip()
                else:
                    dic['半场'] = ''
                # 半角
                lab_corner = data.xpath('./td[7]/text()')
                if lab_corner:
                    dic['半角'] = lab_corner[0].strip()
                else:
                    dic['半角'] = ''
                # 胜负
                win = data.xpath('./td[8]/span/text()')
                if win:
                    dic['胜负'] = win[0].strip()
                else:
                    dic['胜负'] = ''
                # 欧指
                europe = data.xpath('./td[9]/div/div/text()')
                if europe:
                    dic['欧指'] = europe[0].strip()
                else:
                    dic['欧指'] = ''
                # 让球
                rangqiu = data.xpath('./td[10]/div/div/text()')
                if rangqiu:
                    dic['让球'] = rangqiu[0].strip()
                else:
                    dic['让球'] = ''
                # 盘数
                panlu = data.xpath('./td[11]/span/text()')
                if panlu:
                    dic['盘数'] = panlu[0].strip()
                else:
                    dic['盘数'] = ''
                # 进球
                jinqiu = data.xpath('./td[12]/span/text()')
                if jinqiu:
                    dic['进球'] = jinqiu[0].strip()
                else:
                    dic['进球'] = ''
                dict_data['data'].append(dic)
            # 保存数据
            return dict_data

    def __get_recent(self,resp):
        dict_data = {'data': []}
        result_ = re.findall('<div id="recent-record"[\s\S]*?(<tr[\s\S]*?</td>)</tr></table>', resp)
        if not result_:
            dict_data = '暂无数据'
        else:
            result = result_[0]
            html = etree.HTML(result)
            datas = html.xpath('//tr')[1:]
            for data in datas:
                dic = {}
                # 赛事
                event_1 = data.xpath('./td[1]/a/text()')
                if event_1:
                    dic['赛事'] = event_1[0].strip()
                else:
                    dic['赛事'] = ''
                # 时间
                time_1 = data.xpath('./td[2]/text()')
                if time_1:
                    dic['时间'] = time_1[0].strip()
                else:
                    dic['时间'] = ''
                # 主场球队
                home_team_1 = data.xpath('./td[3]/a/span/text()')
                if home_team_1:
                    dic['主场球队'] = home_team_1[0].strip()
                else:
                    dic['主场球队'] = ''
                # 比分
                score = data.xpath('./td[4]/a/span/text()')
                if score:
                    dic['比分'] = score[0] + ':' + score[1]
                else:
                    dic['比分'] = ''
                # 客场球队
                away_team_1 = data.xpath('./td[5]/a/span/text()')
                if away_team_1:
                    dic['客场球队'] = away_team_1[0].strip()
                else:
                    dic['客场球队'] = ''
                # 半场
                half_score = data.xpath('./td[6]/text()')
                if half_score:
                    dic['半场'] = half_score[0].strip()
                else:
                    dic['半场'] = ''
                # 半角
                lab_corner = data.xpath('./td[7]/text()')
                if lab_corner:
                    dic['半角'] = lab_corner[0].strip()
                else:
                    dic['半角'] = ''
                # 胜负
                win = data.xpath('./td[8]/span/text()')
                if win:
                    dic['胜负'] = win[0].strip()
                else:
                    dic['胜负'] = ''
                # 欧指
                europe = data.xpath('./td[9]/div/div/text()')
                if europe:
                    dic['欧指'] = europe[0].strip()
                else:
                    dic['欧指'] = ''
                # 让球
                rangqiu = data.xpath('./td[10]/div/div/text()')
                if rangqiu:
                    dic['让球'] = rangqiu[0].strip()
                else:
                    dic['让球'] = ''
                # 盘数
                panlu = data.xpath('./td[11]/span/text()')
                if panlu:
                    dic['盘数'] = panlu[0].strip()
                else:
                    dic['盘数'] = ''
                # 进球
                jinqiu = data.xpath('./td[12]/span/text()')
                if jinqiu:
                    dic['进球'] = jinqiu[0].strip()
                else:
                    dic['进球'] = ''
                dict_data['data'].append(dic)
        # 保存数据
        return dict_data

    def __get_trend(self, resp):
        html = etree.HTML(resp)
        datas = html.xpath('//div[@id="since-trend"]/div[2]/div')
        dic = {'mgs': []}
        for data in datas:
            team_name = data.xpath('.//span[@class="name"]/text()')[0]
            messages = data.xpath('.//tr')[2:]
            mgs_dic = {'mgs': []}
            mgs_dic['队名'] = team_name
            for mes in messages:
                mgs = {}
                # 类型
                stye = mes.xpath('./td[1]/text()')
                if stye:
                    mgs['类型'] = stye[0]
                else:
                    mgs['类型'] = ''
                # 比赛
                game = mes.xpath('./td[2]/text()')
                if game:
                    mgs['比赛'] = game[0]
                else:
                    mgs['比赛'] = ''
                # 赢盘
                winpan = mes.xpath('./td[3]/text()')
                if winpan:
                    mgs['赢盘'] = winpan[0]
                else:
                    mgs['赢盘'] = ''
                # 走盘
                zoupan = mes.xpath('./td[4]/text()')
                if zoupan:
                    mgs['走盘'] = zoupan[0]
                else:
                    mgs['走盘'] = ''
                # 输盘
                shupan = mes.xpath('./td[5]/text()')
                if shupan:
                    mgs['输盘'] = shupan[0]
                else:
                    mgs['输盘'] = ''
                # 赢盘率
                yingpanlv = mes.xpath('./td[6]/text()')
                if yingpanlv:
                    mgs['赢盘率'] = yingpanlv[0]
                else:
                    mgs['赢盘率'] = ''
                # 大球
                bigball = mes.xpath('./td[7]/text()')
                if bigball:
                    mgs['大球'] = bigball[0]
                else:
                    mgs['大球'] = ''
                # 大球率
                bigballpor = mes.xpath('./td[8]/text()')
                if bigballpor:
                    mgs['大球率'] = bigballpor[0]
                else:
                    mgs['大球率'] = ''
                # 小球
                litterball = mes.xpath('./td[9]/text()')
                if litterball:
                    mgs['小球'] = litterball[0]
                else:
                    mgs['小球'] = ''
                # 小球率
                litterballpor = mes.xpath('./td[10]/text()')
                if litterballpor:
                    mgs['小球率'] = litterballpor[0]
                else:
                    mgs['小球率'] = ''
                mgs_dic['mgs'].append(mgs)
            dic['mgs'].append(mgs_dic)
        return dic

    def __get_situation(self, resp):
        html = etree.HTML(resp)
        # 伤停情况
        datas = html.xpath('//div[@id="injury-situation"]/div[2]/div')
        msg_dic = {'msg': []}
        def __message():
            global dic, name, location, case, start_time, back_time, field_count
            dic = {}
            name = info.xpath('./td[1]/a/span/text()')
            if name:
                dic['球员'] = name[0]
            else:
                dic['球员'] = ''
            location = info.xpath('./td[2]/text()')
            if location:
                dic['位置'] = location[0]
            else:
                dic['位置'] = ''
            case = info.xpath('./td[3]/text()')
            if case:
                dic['原因'] = case[0]
            else:
                dic['原因'] = ''
            start_time = info.xpath('./td[4]/text()')
            if start_time:
                dic['开始时间'] = start_time[0]
            else:
                dic['开始时间'] = ''
            back_time = info.xpath('./td[5]/text()')
            if back_time:
                dic['归队时间'] = back_time[0]
            else:
                dic['归队时间'] = ''
            field_count = info.xpath('./td[6]/text()')
            if field_count:
                dic['影响场数'] = field_count[0]
            else:
                dic['影响场数'] = ''
            return dic

        for data in datas:
            team_name = data.xpath('.//span[@class="name"]/text()')
            infos = data.xpath('.//tr')[1:]
            msg = {'msg': {'伤病': [], '停赛': []}}
            if team_name:
                msg['队名'] = team_name[0]
            else:
                msg['队名'] = ''
            for info in infos:
                if not info.xpath('./td[@colspan="6"]'):
                    if 'td-pd' in info.xpath('./@class')[0]:
                        dic = __message()
                        msg['msg']['伤病'].append(dic)
                    else:
                        dic = __message()
                        msg['msg']['停赛'].append(dic)
            msg_dic['msg'].append(msg)
        return msg_dic

    def __get_league_points(self, resp):
        html = etree.HTML(resp)
        # 联赛积分
        datas = html.xpath('//div[@id="league-points"]/div[2]/div')
        msg = {'msg': []}
        for data in datas:
            dic_msg = {'msg': []}
            team_name = data.xpath('./div[1]/div/a/span/text()')
            event = data.xpath('./div[1]/div/div/text()')
            if team_name and event:
                name = team_name[0] + event[0]
            else:
                name = ''
            dic_msg['队名'] = name
            infos = data.xpath('.//tr')[1:]
            for info in infos:
                dic = {}
                type = info.xpath('./td[1]/text()')
                if type:
                    dic['类型'] = type[0]
                else:
                    dic['类型'] = ''
                changshu = info.xpath('./td[2]/text()')
                if changshu:
                    dic['比赛场数'] = changshu[0]
                else:
                    dic['比赛场数'] = ''
                win_count = info.xpath('./td[3]/text()')
                if win_count:
                    dic['胜场数'] = win_count[0]
                else:
                    dic['胜场数'] = ''
                fail_count = info.xpath('./td[4]/text()')
                if fail_count:
                    dic['负场数'] = fail_count[0]
                else:
                    dic['负场数'] = ''
                ping_count = info.xpath('./td[5]/text()')
                if ping_count:
                    dic['平数'] = ping_count[0]
                else:
                    dic['平数'] = ''
                jinqiu = info.xpath('./td[6]/text()')
                if jinqiu:
                    dic['进球'] = jinqiu[0]
                else:
                    dic['进球'] = ''
                shiqiu = info.xpath('./td[7]/text()')
                if shiqiu:
                    dic['失球'] = shiqiu[0]
                else:
                    dic['失球'] = ''
                jingqiushu = info.xpath('./td[8]/text()')
                if jingqiushu:
                    dic['进球率'] = jingqiushu[0]
                else:
                    dic['进球率'] = ''
                jifen = info.xpath('./td[9]/text()')
                if jifen:
                    dic['积分'] = jifen[0]
                else:
                    dic['积分'] = ''
                paiming = info.xpath('./td[10]/text()')
                if paiming:
                    dic['排名'] = paiming[0]
                else:
                    dic['排名'] = ''
                shenglv = info.xpath('./td[11]/text()')
                if shenglv:
                    dic['胜率'] = shenglv[0]
                else:
                    dic['胜率'] = ''
                dic_msg['msg'].append(dic)
            msg['msg'].append(dic_msg)
        return msg

    def run(self):
        # 用于储存线程
        threads = []
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_live',)))
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_notStart',)))
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_finished',)))
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_other',)))
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_history_events',)))
        threads.append(threading.Thread(target=self.get_events_ID, args=('football_future_events',)))
        # 启动线程
        for thread in threads:
            thread.start()
        # 守护线程
        for thread in threads:
            thread.join()

    @classmethod
    def start(cls):
        st = cls()
        st.run()
        # 每隔一段时间执行一次run方法
        schedule.every(TEST_EVENTS_INTERVAL).seconds.do(st.run)
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == '__main__':
    DataSpider.start()
    # data = DataSpider('football_live')
    # data.get_events_ID()