import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import webbrowser
import threading

from tornado.options import define, options, parse_command_line

port = 6661

clients = {}
client_count = 0
#colors = {'green': False, 'yellow': False}

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        print 'flothandler::get'
        self.render('flot.html')
        
recievedMessage = None

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args):
        global client_count
        client_count += 1
        print 'websockethandler::open'
        self.id = client_count
        #self.set_nodelay(True)
        clients[self.id] = self
    
	#like input_handler
    def on_message(self, message):
        global recievedMessage
        #so that we can access from anywhere, 
        #e.g. shell in a box, or web gui
        message = json.loads(message)
        recievedMessage = message
        print message
		#part of the old test, so commented out
		#colors['yellow'] = message['yellow']
        #colors['green'] = message['green']
        #print 'new color settings:', message
        #send_colors_to_all()
    
    def on_close(self):
        print 'websockethandler::on_close'
        if self.id in clients:
            # remove client from the "list" of clients to notify on color change
            del clients[self.id]
        if not len(clients):
            import sys
            sys.exit()

    def send_message(self, message): 
		self.write_message(json.dumps(message))

def send_message_to_all_clients(message):
    while len(clients) == 0:
        pass
    send_message_to_all(message)
    

def send_message_to_all(message):
    for client in clients.values():
        client.send_message(message)

#needs to be thread to read lines and send to client
class WebServer(threading.Thread):
    def __init__(self, index_handler, *args, **kwargs):
        self._index_handler = index_handler
        self._open_page = kwargs.pop('open_page', True)
        threading.Thread.__init__(self, *args, **kwargs)
    def run(self):
        print 'in webserver'
        app = tornado.web.Application([(r'/', self._index_handler),
	    (r'/socket', WebSocketHandler),(r'/((static|flot|myjQuery).*)', tornado.web.StaticFileHandler, {'path': '.'})])
        print 'before app.listen'
        app.listen(port)
        print 'after app.listen'
        if self._open_page:
            webbrowser.open('http://localhost:%d' % port)
        tornado.ioloop.IOLoop.instance().start()

def startServer():
    server = WebServer(IndexHandler)
    server.setDaemon(True) #runs in background and dies when main thread dies
    server.start()
    
if __name__ == '__main__':
    startServer()
    
    # read lines and send to the web client
    while True:
        s = raw_input()
        send_message_to_all(json.loads(s))

