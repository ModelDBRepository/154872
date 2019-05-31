import webserver
import json
import weakref
import tornado
import threading

index_html = 'console.html'

obj_map = {}

class Widget:
    def _callback(self, data):
        print data

class Text(Widget):
    def __init__(self, text):
        self.text = text
        self.id = None
    def _instantiate(self, parent):
        # TODO: get an id back
        self.id = send_message_blocking(['create', 'label', parent.id, self.text])
        obj_map[self.id] = weakref.ref(self)
        # TODO: transfer any styles

class TextField(Widget):
    def __init__(self, text):
        self.text = text
        self.id = None
    def _instantiate(self, parent):
        # TODO: get an id back
        self.id = send_message_blocking(['create', 'textfield', parent.id, self.text])
        obj_map[self.id] = weakref.ref(self)
        # TODO: transfer any styles
    def set(self, text):
        send_message_to_all(['change', 'value', self.id, text])

class Button(Widget):
    def __init__(self, text, callback):
        self.text = text
        self.id = None
        self.callback = callback
    def _instantiate(self, parent):
        # TODO: get an id back
        self.id = send_message_blocking(['create', 'button', parent.id, self.text])
        obj_map[self.id] = weakref.ref(self)
        # TODO: transfer any styles
    def _callback(self, data):
        self.callback(data)
        #needs to run _callback when you get a callback from onmessage with positive id, need to run _callback with that id, and that onmessage is a new thread, if its not a new thread it needs to be made .

class Graph(Widget):
    def __init__(self):
        self.id = None
    def _instantiate(self, parent):
        self.id = send_message_blocking(['create', 'graph', parent.id])
        obj_map[self.id] = weakref.ref(self)
    def plot(self, data):
        send_message_to_all(['change', 'graph', self.id, data])

class Dialog(Widget):
    def __init__(self, title, max_min=True):
        self.title = title
        self.max_min = max_min
        self.objs = []
        self.id = None
    def add(self, obj):
        self.objs.append(obj)
    def instantiate(self):
        # TODO: get an id back
        self.id = send_message_blocking(['create', 'dialog', self.title, 1 if self.max_min else 0])
        obj_map[self.id] = weakref.ref(self)
        for obj in self.objs:
            obj._instantiate(self)
    def _callback(self, data):
        print data
        
#76-88 need to be replaced
block_condition = threading.Condition()
block_message = None

#will wait until python gets the message
#should send msg, and recieve and return the element's id
#84-91 replace, 
def send_message_blocking(msg):
    webserver.recievedMessage = None
    print 'sending:', msg
    send_message_to_all(msg)
    print 'waiting...'
    while webserver.recievedMessage is None:
        pass
    print 'received:', webserver.recievedMessage
    recievedMessage = webserver.recievedMessage['data'][2]
    return recievedMessage

def send_message_to_all(msg):
    webserver.send_message_to_all_clients(msg)


class index_handler(tornado.web.RequestHandler):
    def get(self):
        # this supports django-like templates, but not using that yet
        self.render(index_html)

class input_handler(tornado.web.RequestHandler):
    def post(self):
        global block_message
        object_id = int(self.get_arguments('object_id')[0])
        data = json.loads(self.get_arguments('data')[0])
        user_id = int(self.get_arguments('userid')[0])
        if object_id >= 0:
            if object_id in obj_map:
                obj = obj_map[object_id]()
                if obj is not None:
                    obj._callback(data)
        else:
            if object_id == -1 and block_message is not None and len(data) == 3 and data[1] == block_message:
                block_condition.acquire()
                block_message = data[-1]
                block_condition.notify()
                block_condition.release()
            else:
                print '(%r, %r, %r)' % (object_id, data, user_id)

server = webserver.WebServer(index_handler, open_page=False)
server.setDaemon(True)
#server.start()
