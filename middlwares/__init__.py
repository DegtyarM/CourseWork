from .middleware import *

middlewares_message = (RegisterCheck(), DatabaseMiddleware(), ThrottlingMiddleware(), AlbumMiddleware(),
                       RedisMiddleware(), ChatActionMiddleware())

middlewares_callback = (RegisterCheck(), DatabaseMiddleware(), RedisMiddleware(), ChatActionMiddleware(),
                        ThrottlingMiddleware())
