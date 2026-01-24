from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter

from pollution_backend.realtime.routing import websocket_urlpatterns


websocket_application = AuthMiddlewareStack(
    URLRouter(websocket_urlpatterns)
)
