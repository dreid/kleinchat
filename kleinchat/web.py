import os

from klein import route, resource, run

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


_clients = {}

@route("/updates")
def updates(request):
    d = Deferred()

    request.setHeader('content-type', 'text/event-stream')

    user = request.getSession(IUser)

    _clients[user] = request

    return d


@route("/favicon.ico")
def favicon(request):
    return ''


@route("/msg")
def msg(request):
    user = IUser(request.getSession())

    for client in _clients:
        updateRequest = _clients[client]

        def writeEvent(message, ur):
            for line in message.split('\n'):
                ur.write('data: ' + line + '\r\n')

            ur.write('\r\n')

        d = renderMessage(user.name, request.args['msg'][0], request)
        d.addCallback(writeEvent, updateRequest)

    return 'ok'


@route("/")
def index(request):
    user = request.getSession(IUser)

    if user.name == None:
        return LoginPage()
    else:
        return ChatPage()


@route("/login")
def login(request):
    session = request.getSession()
    user = IUser(session)
    user.name = request.args['name'][0]

    request.redirect("/")
    request.finish()


if __name__ == '__main__':
    run("localhost", 8080)
