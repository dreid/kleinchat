import os

from klein.decorators import expose
from klein.resource import KleinResource

from twisted.internet.defer import Deferred
from twisted.web.template import Element, XMLFile, renderer, flattenString

from zope.interface import Interface, Attribute, implements
from twisted.python.components import registerAdapter
from twisted.web.server import Session

def template(base):
    return XMLFile(os.path.join(os.path.dirname(__file__), base))

class Base(Element):
    loader = template("base.xml")


class ChatForm(Element):
    loader = template("chat_form.xml")


class ChatPage(Base):
    @renderer
    def body(self, request, tag):
        return ChatForm()


class LoginForm(Element):
    loader = template("login_form.xml")


class LoginPage(Base):
    @renderer
    def body(self, request, tag):
        return LoginForm()


class IUser(Interface):
    name = Attribute("username")

class User(object):
    implements(IUser)

    def __init__(self, session):
        self.name = None

registerAdapter(User, Session, IUser)

class Message(Element):
    loader = template("message.xml")

    def __init__(self, name, message):
        self._name = name
        self._message = message

    @renderer
    def name(self, request, tag):
        return tag(self._name)

    @renderer
    def message(self, request, tag):
        return tag(self._message)


def renderMessage(name, message, request):
    return flattenString(request, Message(name, message))


class KleinChat(KleinResource):
    def __init__(self):
        self.clients = {}

    @expose("/updates")
    def updates(self, request):
        d = Deferred()

        request.setHeader('content-type', 'text/event-stream')

        user = request.getSession(IUser)

        if user not in self.clients:
            self.clients[user] = request

        return d

    @expose("/favicon.ico")
    def favicon(self, request):
        return ''

    @expose("/msg")
    def msg(self, request):
        user = IUser(request.getSession())

        for client in self.clients:
            updateRequest = self.clients[client]
            def writeEvent(message):
                for line in message.split('\n'):
                    updateRequest.write('data: ' + line + '\r\n')

                updateRequest.write('\r\n')

            d = renderMessage(user.name, request.args['msg'][0], request)
            d.addCallback(writeEvent)

        return 'ok'

    @expose("/")
    def index(self, request):
        user = request.getSession(IUser)

        if user.name == None:
            return LoginPage()
        else:
            return ChatPage()

    @expose("/login")
    def login(self, request):
        session = request.getSession()
        user = IUser(session)
        user.name = request.args['name'][0]
        print user.name, session.uid

        request.redirect("/")
        request.finish()
