import nonebot
from nonebot_adapter_gocq import Bot as CQHTTPBot


nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter("gocq", CQHTTPBot)
nonebot.load_plugins("src/plugins")


app = nonebot.get_asgi()


if __name__ == "__main__":
    nonebot.run()