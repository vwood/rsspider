from google.appengine.dist import use_library
use_library('django', '1.2')

import os
import cgi
import datetime
import urllib
import wsgiref.handlers

from google.appengine.api import users 
from google.appengine.ext import db 
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

ITEMS_PER_PAGE = 10

class Board(db.Model):
    """Models a board with: name and description."""
    link = db.StringProperty()
    name = db.StringProperty()
    description = db.TextProperty()

class Thread(db.Model):
    """Models a thread with:
    link, title and author."""
    link = db.StringProperty()
    title = db.StringProperty()
    author = db.UserProperty()

class Post(db.Model):
    """Models a post entry with:
    an author, link, content, and date."""
    author = db.UserProperty()
    link = db.StringProperty()
    content = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)

def board_key(board_name=None):
    """Builds a datastore key for a 
    Board entity with board_name."""
    return db.Key.from_path('Board', board_name or 'default_board')

def thread_key(thread_name=None):
    """Builds a datastore key for a 
    Thread entity with thread_name."""
    return db.Key.from_path('Thread', thread_name or 'default_thread')

def user_login(url):
    """Constructs a login or logout message."""
    user = users.get_current_user()
    if user is None:
        return "<a href=\"%s\">login</a>" % users.create_login_url(url)
    else:
        return "Signed in as %s. <a href=\"%s\">logout</a>" % (user.nickname(), users.create_logout_url(url))

class RequestBase(webapp.RequestHandler):
    def ensure_user_logged_in(self):
        user = users.get_current_user()
        if user is None:
            self.redirect(users.create_login_url(self.request.url))

### POSTS ###
class CreatePost(RequestBase):
    def post(self):
        self.ensure_user_logged_in()
        thread_name = self.request.get('thread_name')
        post = Post(parent=thread_key(thread_name))

        if users.get_current_user():
            post.author = users.get_current_user()
        
        post.content = self.request.get('content')
        post.put()
        self.redirect('/thread?' + urllib.urlencode({'name': thread_name}))

### THREADS ###
class CreateThread(RequestBase):
    def post(self):
        self.ensure_user_logged_in()
        board_name = self.request.get('board_name')
        thread_name = self.request.get('title').lower().replace(" ", "_")

        thread = Thread(parent=board_key(board_name), key_name=thread_name)
        thread.link = thread_name
        thread.title = self.request.get('title')
        if users.get_current_user():
            thread.author = users.get_current_user()
        thread.put()
        self.redirect('/thread?' + urllib.urlencode({'name' : thread_name}))

class GetThread(RequestBase):
    def get(self):
        thread = db.GqlQuery("SELECT * FROM Thread WHERE link = :1", 
                             self.request.get('name')).get()

        if thread is None:
            path = os.path.join(os.path.dirname(__file__), 'static/html/thread_notfound.html')
            self.response.out.write(template.render(path, {}))
        else:
            try:
                offset = int(self.request.get('offset'))
            except:
                offset = 0
            post_query = Post.all().ancestor(thread_key(thread.link)).order('-date')
            posts = post_query.fetch(ITEMS_PER_PAGE, max(offset, 0))

            values = {'board': thread.parent(), 
                      'thread': thread, 
                      'posts': posts, 
                      'user_login': user_login(self.request.url),
                      'offset': offset}
            path = os.path.join(os.path.dirname(__file__), 'static/html/thread.html')
            self.response.out.write(template.render(path, values))

### BOARDS ###
class CreateBoard(RequestBase):
    def post(self):
        self.ensure_user_logged_in()
        safename = self.request.get('name').lower().replace(" ", "_")

        board = Board(key_name = safename)
        board.link = safename
        board.name = self.request.get('name')
        board.description = self.request.get('content')
        board.put()
        self.redirect('/index')

class GetBoard(RequestBase):
    def get(self):
        board_name = self.request.get('name')
        board = db.GqlQuery("SELECT * FROM Board WHERE link = :1", 
                            board_name).get()

        if board is None:
            path = os.path.join(os.path.dirname(__file__), 'static/html/board_notfound.html')
            self.response.out.write(template.render(path, {}))
        else:
            try:
                offset = int(self.request.get('offset'))
            except:
                offset = 0
            thread_query = Thread.all().ancestor(board_key(board_name))
            threads = thread_query.fetch(ITEMS_PER_PAGE, max(offset, 0))

            values = {'board': board,
                      'threads': threads,
                      'user_login': user_login(self.request.url),
                      'offset':offset}
            path = os.path.join(os.path.dirname(__file__), 'static/html/board.html')
            self.response.out.write(template.render(path, values))

class BoardIndex(RequestBase):
    def get(self):
        try:
            offset = int(self.request.get('offset'))
        except:
            offset = 0
        board_query = db.GqlQuery("SELECT * FROM Board")
        boards = board_query.fetch(ITEMS_PER_PAGE, max(offset, 0))
        values = {'boards': boards,
                  'user_login': user_login(self.request.url),
                  'offset': offset}

        path = os.path.join(os.path.dirname(__file__), 'static/html/index.html')
        self.response.out.write(template.render(path, values))

application = webapp.WSGIApplication(
    [('/', BoardIndex),
     ('/index', BoardIndex),
     ('/create_board', CreateBoard),
     ('/create_thread', CreateThread),
     ('/create_post', CreatePost),
     ('/thread', GetThread),
     ('/board', GetBoard)])

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
