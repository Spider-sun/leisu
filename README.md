## 雷速体育实时数据抓取



### 项目要求

1.实时抓取 - 足球（篮球）比分数据和logo等图标，赛事、时间、状态、主场球队、比分、客场球队、半场、角球、三合一数据等；

2.历史未来数据 - 抓取历史三天的赛事情况，及未来一周的赛事赛程；

3.分析页面 - 历史交锋、近期战绩、联赛积分、盘路走势、伤停情况等；

4.技术统计（实时） - 文字直播和球队阵容，及上方其他信息； 

5.足球、篮球资料库信息（属于一次性的数据，抓完保存本地数据库中），长期抓取。

### 设计思路

1.Redis数据库作为缓存数据库，MongoDB数据库作为存储数据库；

2.将实时抓取和历史未来的赛事放在MongDB数据库中，并将其赛事ID存储到Redis数据库；

3.通过赛事ID，分别获取分析页面、技术统计的内容，并将其数据保存到MongoDB数据库中；

4.通过查询MongoDB数据库的不同集合的赛事ID，获取到赛事的比分数据、分析数据及技术统计。

### 数据结构

1.db数据库文件：写入Redis和MongoDB数据库的增删改查的方法，用作于操作数据库的接口；

2.RedisSpiders缓存数据爬虫文件：分别写入实时抓取及历史未来数据的爬虫文件，并提取出每条 赛事信息，将赛事信息保存到MongoDB数据库下的football下的homepage集合下，并将其赛事ID保存到Redis数据库中，用于后续其他数据的抓取；

3.DataSpiders数据爬虫文件：创建三个爬虫文件，分别获取三合一数据、分析页面、技术统计数据。从Redis数据库中获取要爬取的赛事的ID，并请求获取其三个网页的信息，获取三合一数据、分析页面数据、及技术统计数据，并分别保存到MongoDB数据库的football下的index、shujufenxi、event_info、集合中；

4.WipeCache过期数据检测文件：用于定时检测MongDB数据库的过期数据，并清除；

5.IP_API文件：ip接口，用于项目的ip更换，以维持项目的稳定抓取；

6.settings配置文件：用于配置项目的数据库地址、线程及异步数量等配置；

7.main项目启动入口：通过多进程启动每个爬虫，该模块为启动整个项目的入口。

### 实现步骤

1.实时抓取数据爬虫：通过对主页源代码的分析得知，该主页信息的数据是通过JS加载的，通过requests对网站发起请求，获取其网页源代码。使用正则表达式获取其JS下的JSON格式信息，再通过不同字典的key - value匹配获取赛事的主场、客场、比分等数据；

2.历史未来数据爬虫：通过对历史、未来赛事网页分析，分别requests向网页发起请求，通过xpath对网页数据进行提取，获取其赛事的主场、客场、比分等数据；

3.技术统计数据爬虫：通过线程threading分别从Redis数据库中获取今日实时赛事ID和历史未来赛事ID，并分别将赛事ID加入队列，通过对技术统计网页的分析，得知该网页数据是通过Ajax加载的，通过浏览器抓包，获取该网页数据接口，从队列中取出赛事ID，通过异步回调的方法，不断访问网页接口获取数据，过滤整理后获得文字直播内容及球队阵容信息，并接入数据库，并使用schedule模块使今日实时赛事的线程每三秒刷新一次，历史及未来赛事的线程每天凌晨十二点刷新一次；

4.三合一数据爬虫：通过线程threading分别从Redis数据库中获取今日实时赛事ID和历史未来赛事ID，并分别将赛事ID加入队列，通过异步回调的方法，不断地通过字符串拼接获取并访问网页，获取其网页源代码，并通过xpath提取出三合一数据，接入数据库，并使用schedul模块使今日赛事的线程每三秒刷新一次，历史及未来赛事的线程每天凌晨十二点刷新一次；

5.分析页面数据爬虫：获取Redis数据库中的所有赛事ID并加入队列，通过在队列中获取赛事ID，拼接成页面分析网页并访问，获取其网页源代码，通过re和xpath获取其网页的历史交锋、近期战绩、联赛积分、盘路走势、伤停情况等信息，保存至数据库中，爬虫默认每两小时爬取一次；

6.过期数据检测：通过对MongoDB数据库下HomePage集合中的数据检测，并通过时间的比对，查找到四天及以前的数据，通过其赛事ID，将其他集合下的该赛事数据清除，该文件每天零点刷新；

7.main项目启动入口：将上面每个爬虫文件导入该文件，并通过multiprocessing中的Process创建多进程，启动每一个爬虫文件。



账号: Cruiser.ydlkr@gradesec.com
密码: Digit123456
