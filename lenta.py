# -*- coding: utf-8 -*-

import json
import time
import random
import mechanize
import feedparser
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

# result['comment_id'] result['status'] == 'ok'

@route('/')
def index():
    return static_file('index.html', root='')

@route('/news/')
def news():
    feed = feedparser.parse('http://lenta.ru/rss/')
    items = feed['items']
    items.sort(key=lambda item: item['published_parsed'])
    
    output = map(lambda item: {
        'title': item['title'],
        'url': item['link'],
        'summary': item['summary'],
        'time': time.strftime('%H:%M', item['published_parsed']),
    }, items)
    
    return json.dumps(output)

@post('/comment/')
def comment():
    client = random.choice(clients)
    return ''

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
