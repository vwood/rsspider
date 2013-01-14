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

ITEMS_PER_PAGE = 40

class Link(db.Model):
    """Models a link entry with:
    an author, link, content, and date."""
    author = db.UserProperty()
    link = db.StringProperty()
    description = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)

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

class CreateLink(RequestBase):
    def post(self):
        self.ensure_user_logged_in()
        link = Link()

        if users.get_current_user():
            link.author = users.get_current_user()
        
        link.link = self.request.get('link')
        link.description = self.request.get('description')
        link.put()
        self.redirect('/index')

class LinkIndex(RequestBase):
    def get(self):
        try:
            offset = int(self.request.get('offset'))
        except:
            offset = 0

        link_query = db.GqlQuery("SELECT * FROM Link")
        links = link_query.fetch(ITEMS_PER_PAGE, max(offset, 0))
        has_more = link_query.count() > ITEMS_PER_PAGE + offset 
        
        values = {'links': links,
                  'user_login': user_login(self.request.url),
                  'offset': offset,
                  'has_more': has_more}

        path = os.path.join(os.path.dirname(__file__), 'static/html/index.html')
        self.response.out.write(template.render(path, values))

application = webapp.WSGIApplication(
    [('/', LinkIndex),
     ('/index', LinkIndex),
     ('/create_link', CreateLink)])

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
