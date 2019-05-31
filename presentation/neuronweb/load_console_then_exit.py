import webserver
import tornado
import sys
import time

has_loaded = False

class index_handler(tornado.web.RequestHandler):
    def get(self):
        global has_loaded
        # this supports django-like templates, but not using that
        self.render('console.html')
        has_loaded = True

        
class input_handler(tornado.web.RequestHandler):
    def post(self):
        pass

server = webserver.WebServer(index_handler, open_page=True)
server.setDaemon(True)
server.start()

# should be long enough, but allows timing out
for i in xrange(20):
    if has_loaded:
        # give it a little more time to be sure everything has transmitted, then exit
        time.sleep(0.25)
        sys.exit()
    time.sleep(.5)
    
