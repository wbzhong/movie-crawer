import MovieUtils
import requests
import re
import random
from time import sleep
from bs4 import BeautifulSoup
import mysql.connector

DEFAULT_TIMEOUT = 10                # 默认等待时间
conn = mysql.connector.connect(user='root', password='621374as', database='movie')
cursor = conn.cursor()

def crawCurrentMovie():
    '''
    获取当前正在上映的电影
    :return: 返回一组正在上映电影的ID  List格式
    '''
    url = 'http://www.cbooo.cn/'
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
        }
    text = ''
    movieIDList = []
    print('Crawing current movie...')
    # 抓取整个网页
    try:
        print('Requesting url: ', url)
        text = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT).text
    except:
        print('Error when request url=', url)
        return None
    # 解析电影的ID
    soup = BeautifulSoup(text, "lxml")                      # 把网页保存为一个BeautifulSoup对象
    results = soup.find_all('tr', class_='trtop', onmouseover='ChangeTopR(this.id)')
    for result in results:
        print(result['id'])
        movieIDList.append(result['id'])
    return movieIDList

def crawMovie(movieID):
    '''
    根据电影的ID,爬取电影的信息
    包括 名称,类型,片长,制式,导演,主演,制作公司,发行公司
    :param movieID: CBO上电影的ID
    :return:一个Dict,存储有电影的信息
    '''
    url = 'http://www.cbooo.cn/m/' + str(movieID)
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
        }
    text = ''
    movieDataDict = {'id':movieID,
                     'cname':None,
                     'ename':None,
                     'type':None,
                     'length':None,
                     'releasetime':None,
                     'standard':None,
                     'director':None,
                     'actor':None,
                     'producer':None,
                     'publisher':None,
                     'sumboxoffice':None}
    print('Crawing movie info ', url)
    # 抓取整个网页
    try:
        text = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT).text
    except:
        print('Error when request url=', url)
        return None
    # 解析电影的信息
    soup = BeautifulSoup(text, "lxml")
    result1 = soup.find('div', class_='cont')               # 标题等信息
    result2 = soup.find('dl', class_='dltext')
    result2 = result2.find_all('dd')
    #print(result1.h2.text)
    i = 0
    isSumBoxOffice = False
    for element in result1.stripped_strings:
        if isSumBoxOffice == True:
            movieDataDict['sumboxoffice'] = int(float(element[0:-1]) * 10000)
            isSumBoxOffice = False
        elif i == 0:
            movieDataDict['cname'] = element
        elif i == 2:
            movieDataDict['ename'] = element
        elif element[0] == '类':
            movieDataDict['type'] = element[3:]
        elif element[0] == '片':
            movieDataDict['length'] = element.replace('\r','').replace('\n','').replace(' ', '')[3:-3]
        elif element[0] == '上':
            # 需要处理字符串成日期的形式
            movieDataDict['releasetime'] = MovieUtils.str2date(element[5:-4])
        elif element[0] == '制':
            movieDataDict['standard'] = element[3:]
        elif element[0] == '累':
            isSumBoxOffice = True
        i = i + 1

    i = 0
    for element in result2:
        '''
        i = 0: 导演
            1: 主演
            2: 制作公司
            3: 发行公司
        '''
        memberList = []
        rank = 0
        links = element.find_all('a')
        for link in links:
            rank = rank + 1
            idMatched = re.match(r'^(http://www.cbooo.cn/(p|c)/)(\d+)$', link['href'])
            if idMatched:
                memberList.append({'id':int(idMatched.group(3)), 'rank':rank})

        if i == 0:
            movieDataDict['director'] = memberList
        elif i == 1:
            movieDataDict['actor'] = memberList
        elif i == 2:
            movieDataDict['producer'] = memberList
        elif i == 3:
            movieDataDict['publisher'] = memberList
        i = i + 1
    print(movieDataDict)
    return movieDataDict

def saveMovieInDatabase(movieDataDict):
    print('Saving movie # ', movieDataDict['id'], ' into data base...')
    cursor.execute('SET FOREIGN_KEY_CHECKS=0')      # 关闭外键检测
    conn.commit()
    try:
        cursor.execute(
            'replace into movie'
            '(MovieID, CName, EName, Type, Length, ReleaseTime, Standard, SumBoxOffice)'
            'values (%s, %s, %s, %s, %s, %s, %s, %s)',
            [movieDataDict['id'], movieDataDict['cname'], movieDataDict['ename'],
             movieDataDict['type'], movieDataDict['length'], movieDataDict['releasetime'],
             movieDataDict['standard'], movieDataDict['sumboxoffice']]
        )
        conn.commit()
    except Exception as e:
        print('Error in saveMovieInDatabase Step 1.')
        print(e)
    for person in movieDataDict['director']:
        try:
            cursor.execute(
                'replace into movie_actor'
                '(MovieID, ActorID, Rank, Role)'
                'values (%s, %s, %s, %s)',
                [movieDataDict['id'], person['id'], person['rank'], 'director']
            )
            conn.commit()
        except Exception as e:
            print('Error in saveMovieInDatabase Step 2 director.')
            print(e)
    for person in movieDataDict['actor']:
        try:
            cursor.execute(
                'replace into movie_actor'
                '(MovieID, ActorID, Rank, Role)'
                'values (%s, %s, %s, %s)',
                [movieDataDict['id'], person['id'], person['rank'], 'actor']
            )
            conn.commit()
        except Exception as e:
            print('Error in saveMovieInDatabase Step 3 actor.')
            print(e)
    for person in movieDataDict['producer']:
        try:
            cursor.execute(
                'replace into movie_company'
                '(MovieID, CompanyID, Rank, Role)'
                'values (%s, %s, %s, %s)',
                [movieDataDict['id'], person['id'], person['rank'], 'producer']
            )
            conn.commit()
        except Exception as e:
            print('Error in saveMovieInDatabase Step 4 producer.')
            print(e)
    for person in movieDataDict['publisher']:
        try:
            cursor.execute(
                'replace into movie_company'
                '(MovieID, CompanyID, Rank, Role)'
                'values (%s, %s, %s, %s)',
                [movieDataDict['id'], person['id'], person['rank'], 'publisher']
            )
            conn.commit()
        except Exception as e:
            print('Error in saveMovieInDatabase Step 5 publisher.')
            print(e)
    cursor.execute('SET FOREIGN_KEY_CHECKS=1')      # 重新开启外键检测
    conn.commit()


def crawActor(actorID):
    '''
    根据演员的ID,爬取演员信息
    包括 名称,已发布作品,未发布作品
    :param actorID:
    :return:
    '''
    pass

def main():
    # get movie IDs
    movieIDList = crawCurrentMovie()
    # get movie data
    movieDataList = []
    for movieID in movieIDList:
        movieDataList.append(crawMovie(movieID))
    # save movie data into data base
    for movieData in movieDataList:
        saveMovieInDatabase(movieData)
    cursor.close()
    conn.close()
    return

if __name__ == '__main__':
    main()
