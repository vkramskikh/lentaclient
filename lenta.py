# -*- coding: utf-8 -*-

import json
import time
import random
import httplib
import calendar
import threading
import mechanize
import feedparser
from StringIO import StringIO
from gzip import GzipFile
from BeautifulSoup import BeautifulSoup
from bottle import request, get, post, route, run, static_file

from users import users

class LentaClient(object):
    def __init__(self):
        self.browser = mechanize.Browser()
        self.logged_in = False

    def login(self, login, password):
        self.browser.open('http://id.lenta.ru/login/')
        self.browser.select_form(name='login')
        self.browser['login'] = login
        self.browser['password'] = password
        self.browser.submit()
        if self.browser.geturl() == 'http://id.lenta.ru/':
            self.logged_in = True

    def comment(self, news_id, text, parent_id=None):
        self.browser.open('http://readers.lenta.ru/news/%s/' % news_id)
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'reply_form')
        self.browser.form.action = 'http://readers.lenta.ru/post_comment/'

        self.browser['text'] = text
        if parent_id is not None:
            self.browser.form.find_control('parent_id').readonly = False
            self.browser['parent_id'] = str(parent_id)

        response = self.browser.submit()

        result = json.loads(response.read(), encoding='windows-1251')
        return result

    def count_comments(self, news_id):
        url = 'http://readers.lenta.ru/news/%s/' % news_id
        self.browser.open(url)
        return len([link for link in self.browser.links(url_regex=r'\./\?thread_id=\d+')])


@route('/')
def index():
    return static_file('index.html', root='')

@route('/static/<file>')
def static(file):
    return static_file(file, root='')

@route('/news_rss/')
def news_rss():
    feed = feedparser.parse('http://lenta.ru/rss/')
    items = feed['items']
    items.sort(key=lambda item: item['published_parsed'])
    output = map(lambda item: {
        'title': item['title'],
        'url': item['link'],
        'summary': item['summary'],
        'time': time.strftime('%H:%M', time.localtime(calendar.timegm(item['published_parsed']))),
    }, items)

    return json.dumps(output)

@route('/news/')
def news():
    class ParserThread(threading.Thread):
        def __init__(self, category):
            self.category = category
            self.news = None
            super(ParserThread, self).__init__()

        def run(self):
            conn = httplib.HTTPConnection('lenta.ru')
            conn.request('GET', '/%s/' % self.category, headers={'Accept-Encoding': 'gzip,deflate'})
            response = conn.getresponse()
            if response.getheader('Content-Encoding', '') == 'gzip':
                html = GzipFile(fileobj=StringIO(response.read())).read()
            else:
                html = response.read()
            conn.close()

            soup = BeautifulSoup(html, fromEncoding='windows-1251')
            news_list = soup.find('td', {'class': 'razdel-news'})
            first_news = news_list.find('div', {'class': 'news0'})
            other_news = news_list.findAll('div', {'class': 'news1'})

            self.news = map(lambda item: {
                'title': item.find(lambda tag: tag.name[0] == 'h').a.string,
                'url': 'http://lenta.ru/%s/' % item.find('a')['href'],
                'summary': item.find('p').string,
                'time': time.strptime(item.find('div', {'class': 'dt'}).string, '%d.%m %H:%M'),
            }, [first_news] + other_news)

    threads = []
    for category in ['politic', 'russia']:
        thread = ParserThread(category)
        thread.start()
        threads.append(thread)

    news = []
    for thread in threads:
        thread.join()
        if thread.news:
            news += thread.news

    news.sort(key=lambda item: item['time'])

    for item in news:
        item['time'] = time.strftime('%d.%m %H:%M', time.gmtime(calendar.timegm(item['time']))),

    return json.dumps(news)

@post('/comment/')
def comment():
    client = random.choice(clients)
    result = client.comment(
        request.forms.get('news_id'),
        request.forms.get('text'),
        request.forms.get('parent_id', 0)
    )
    return json.dumps(result)

@route('/count_comments/<news_id:re:[a-z\d\/]+>')
def comment(news_id):
    client = random.choice(clients)
    return str(client.count_comments(news_id))

if __name__ == "__main__":
    clients = []
    for user in users:
        client = LentaClient()
        client.login(*user)
        if client.logged_in:
            clients.append(client)
        else:
            print "User %s is no longer valid" % user[0]

    run(host='localhost', port=8080)
