import MovieUtils
import requests
import re
import execjs   # execute javascript from python
import datetime #
import mysql.connector
from datetime import datetime, timedelta

DEFAULT_TIMEOUT = 10                # 默认等待时间

conn = mysql.connector.connect(**MovieUtils.DBCONFIG)
cursor = conn.cursor()

def getCinemaShowtime(cinemaId, date):
    '''
    根据影院ID和日期，获取该影院该日的拍片情况
    :param cinemaId: 影院ID
    :param date: 日期，格式为 20170404
    :return: 一个dict，可通过['value']['showtimes']得到showtimes
    '''
    url = 'http://service.theater.mtime.com/Cinema.api?Ajax_CallBack=true' \
          '&Ajax_CallBackType=Mtime.Cinema.Services&Ajax_CallBackMethod=GetShowtimesJsonObjectByCinemaId&' \
          'Ajax_CallBackArgument0=' + str(cinemaId) + '&Ajax_CallBackArgument1=' + str(date)
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
    text = ''
    movieIDList = []
    # 抓取整个网页
    try:
        print('Requesting url: ', url)
        text = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT).text
    except:
        print('Error when request url=', url)
        return None
    var = re.match(r'^var GetShowtimesJsonObjectByCinemaResult = (.+);', text).group(1)     # 获取javascript值
    if var:
        var = execjs.eval(var)      # 用库处理js值
        return var
    return None

def getMovieInfoFromMtime(mtimeMovieID):
    '''
    根据时光网的movieID，获得电影的中英文名
    :param mtimeMovieID: 时光网的movieID
    :return: 一个dict,包含movieID和中英文名
    '''
    url = 'http://service.library.mtime.com/Movie.api?Ajax_CallBack=true&Ajax_CallBackType=Mtime.Library.Services&' \
          'Ajax_CallBackMethod=GetOnlineTicketByMovieId&Ajax_CallBackArgument0=' + str(mtimeMovieID)
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
    text = ''
    dict = {
        'MovieID' : mtimeMovieID,
        'CName' : None,
        'EName' : None
    }
    try:
        print('Requesting url: ', url)
        text = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT).text
    except:
        print('Error when request url=', url)
        return None
    var = re.match(r'^var GetOnlineTicketByMovieIdResult = (.+);', text).group(1)
    if var:
        var = execjs.eval(var)
    else:
        return dict
    try:
        if 'titlecn' in var['value']:
            dict['CName'] = var['value']['titlecn']
        if 'titleen' in var['value']:
            dict['EName'] = var['value']['titleen']
    except Exception as e:
        print(e)
    return dict

def saveShowtime(showtime, cinemaID):
    dict = {
        'CinemaID': cinemaID,
        'MtimeMovieID': None,
        'ID': None,             # 可以用来查该场次座位情况 http://piao.mtime.com/onlineticket/showtime/ID/
        'ShowtimeID': None,
        'HallID': None,
        'SeatCount': None,
        'HallName': None,
        'Language': None,
        'StartTime': None,
        'EndTime': None,
        'Price': None,
        'Version': None
    }
    try:
        dict['MtimeMovieID'] = showtime['movieId']
        dict['ID'] = showtime['id']
        dict['ShowtimeID'] = showtime['showtimeId']
        dict['HallID'] = showtime['hallId']
        dict['SeatCount'] = showtime['seatCount']
        dict['HallName'] = showtime['hallName']
        dict['Language'] = showtime['language']
        dict['StartTime'] = showtime['realtime']
        dict['EndTime'] = showtime['movieEndTime']
        dict['Price'] = showtime['mtimePrice']
        dict['Version'] = showtime['version']
    except Exception as e:
        print(e)
    # save into db
    cursor.execute('SET FOREIGN_KEY_CHECKS=0')      # 关闭外键检测
    conn.commit()
    try:
        cursor.execute(
            'replace into showtime'
            '(CinemaID, MtimeMovieID, ID, ShowtimeID, HallID, SeatCount, HallName, Language, StartTime, EndTime, Price, Version)'
            'values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            [dict['CinemaID'], dict['MtimeMovieID'], dict['ID'], dict['ShowtimeID'], dict['HallID'], dict['SeatCount'], dict['HallName'],
            dict['Language'], dict['StartTime'], dict['EndTime'], dict['Price'], dict['Version']]
        )
        conn.commit()
    except Exception as e:
        print('Error in saveShowtime.')
        print(e)
    finally:
        cursor.execute('SET FOREIGN_KEY_CHECKS=1')  # 重新开启外键检测
        conn.commit()

def carweAndSaveMtimeMovieInfo():
    cursor.execute('SELECT DISTINCT MtimeMovieID FROM showtime')
    movieIdList = cursor.fetchall()
    # craw
    for tuple in movieIdList:
        dict = getMovieInfoFromMtime(tuple[0])
        try:
            cursor.execute('SET FOREIGN_KEY_CHECKS=0')      # 关闭外键检测
            cursor.execute(
                'replace into movie_mtime'
                '(MtimeMovieID, EName, CName)'
                'values (%s, %s, %s)',
                [dict['MovieID'], dict['EName'], dict['CName']]
            )
            conn.commit()
        except Exception as e:
            print('Error in SaveMtimeMovieInfo.')
            print(e)
        finally:
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')  # 重新开启外键检测
            conn.commit()

def saveMovies(movies):
    '''
    传入一个movie list
    读取数据库中已经存在的movie
    存入没有存入的movie
    :param movies: movie list
    :return:
    '''
    cursor.execute('SELECT DISTINCT MtimeMovieID FROM movie_mtime')
    movieIdList = cursor.fetchall()
    # craw
    movieIdList = [tuple[0] for tuple in movieIdList]

    for movie in movies:
        if movie['movieId'] not in movieIdList:
            # save movie
            saveMovie(movie)


def saveMovie(movieDict):
    try:
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')      # 关闭外键检测
        cursor.execute(
            'replace into movie_mtime'
            '(MtimeMovieID, EName, CName, Type, Length, Director, Year)'
                'values (%s, %s, %s, %s, %s, %s, %s)',
            [movieDict['movieId'], movieDict['movieTitleCn'], movieDict['movieTitleEn'],
             movieDict['property'], movieDict['runtime'][0:-2], movieDict['director'], movieDict['year']]
        )
        conn.commit()
    except Exception as e:
        print('Error in SaveMtimeMovieInfo.')
        print(e)
    finally:
        cursor.execute('SET FOREIGN_KEY_CHECKS=1')  # 重新开启外键检测
        conn.commit()

def saveShowtimesAndMovie(cinemaShowtimes):
    if cinemaShowtimes == None:
        return
    # ========== Save Movies ==========
    saveMovies(cinemaShowtimes['value']['movies'])

    # ========== Save Showtimes ==========
    # 截取showtimes
    cinemaId = cinemaShowtimes['value']['cinemaId']
    cinemaShowtimes = cinemaShowtimes['value']['showtimes']
    for showtime in cinemaShowtimes:
        saveShowtime(showtime, cinemaId)

def getCinemaList(cityID):
    '''
    返回一个list，每个成员是一个tuple
    :param cityID:
    :return:
    '''
    cursor.execute('SELECT CinemaID FROM cinema WHERE CityID = %s', (cityID,))
    cinemaList = cursor.fetchall()
    return cinemaList

def execute():
    '''
    执行函数
    :return:
    '''
    # 获取要爬取的日期
    now = datetime.now().date()             # 当前日期
    next = now + timedelta(days=1)          # 明天
    now = int(MovieUtils.str2date(str(now)))
    next = int(MovieUtils.str2date(str(next)))
    # 爬取
    for date in [now, next]:
        print('# Crawing date #', date)
        for cityID in MovieUtils.CRAWING_CITIES:
            print('## Crawing city #', cityID)
            cinemas = getCinemaList(cityID)
            for cinema in cinemas:
                print('### Crawing cinema #', cinema[0])
                saveShowtimesAndMovie(getCinemaShowtime(cinema[0], date))
    carweAndSaveMtimeMovieInfo()

    cursor.close()
    conn.close()

if __name__ == '__main__':
    execute()

