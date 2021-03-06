import MovieUtils
import requests
import mysql.connector
import json

DEFAULT_TIMEOUT = 10
conn = mysql.connector.connect(**MovieUtils.DBCONFIG)
cursor = conn.cursor()

def crawhistoryScene(month,day,city):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
    }
    url = 'http://ebotapp.entgroup.cn/Schedule/GetRowPiece_MovieByShowCount?http://ebotapp.entgroup.cn/Schedule/GetRowPiece_MovieByShowCount?' + 'CinemaID=&PageIndex=1&PageSize=50&_ServicePrice=&_Date=2017-' + str(month) +'-'+ str(day) +'&_DateSort=Day&_sDate=2017-' + str(month) + '-'+ str(day) +'&_eDate=2017-' + str(month) +'-'+ str(day) +'&_Line=&_City='+ str(city) +'&_CityLevel=&_ScreenFormat=&_ShowType=&RowPieceType=1'
    # 75上海，18北京，200广州，202深圳，241成都，90杭州，77南京，172武汉，346天津，239重庆，139青岛，186长沙，119厦门
    CityDict = {
        '75' : '上海市','18' : '北京市','200' : '广州市','202' : '深圳市','241' : '成都市','90' : '杭州市','77' : '南京市','172' : '武汉市',
        '346' : '天津市','239' : '重庆市','139' : '青岛市','186' : '长沙市','119' : '厦门市'
    }
    SceneList = []
    print('Crawing Sceneincity : ', url)
    text = ''
    try:
        text = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT).text
    except:
        print('Error when request url=', url)
        return None
    data = json.loads(text)
    db = data['data2']
    for element in db:
        SceneDist = {
            'MovieID': None,
            'CityName': CityDict[city],
            'Date': MovieUtils.str2date('2017' + '-' + str(month) + '-' + str(day)),
            'Scene': None
        }
        SceneDist['MovieID'] = element['EnMovieID']
        SceneDist['Scene'] = element['IndexValue']
        SceneList.append(SceneDist)
    pass

    return SceneList

def saveSceneInDatabase(SceneList):
    cursor.execute('SET FOREIGN_KEY_CHECKS=0')
    conn.commit()
    for scene in SceneList:
        try:
            print('Saving scene # ', scene['MovieID'], 'into data base')
            cursor.execute(
                'replace into movie_scene'
                '(MovieID,CityName,SceneDate,Scene)'
                'values (%s, %s ,%s ,%s)',
                [scene['MovieID'], scene['CityName'], scene['Date'], scene['Scene']]
            )
            conn.cursor()
        except Exception as e:
            print('Error in saveSceneInDatabase Step')
            print(e)

def main():
    # 需要注意的是，这个ID并不与数据库中的city表相对应！！！！！
    # 75->292,290,365,366,880,974,628,561,293,291,829,598,323
    cityID = ['75','18','200','202','241','90','77','172','346','239','139','186','119']
    for city in range(0,13):
        for day in range(1,17):
            saveSceneInDatabase(crawhistoryScene(4,day,cityID[city]))
        for day in range(1,32):
            saveSceneInDatabase(crawhistoryScene(3,day,cityID[city]))
        for day in range(1,29):
            saveSceneInDatabase(crawhistoryScene(2,day,cityID[city]))
        pass


if __name__ == '__main__':
    main()


