import asyncio
from db.db import DB
from bot import TG_Bot
from db.storage import UserStorage, OrderStorage
from config import Config


async def init_db():
    db = DB(
        host=Config.HOST,
        port=Config.PORT,
        login=Config.LOGIN,
        password=Config.PASSWORD,
        database=Config.DATABASE,
    )
    await db.init()
    user_storage = UserStorage(db)
    await user_storage.init()
    order_storage = OrderStorage(db)
    await order_storage.init()
    return user_storage, order_storage


async def main():
    user_storage, order_storage = await init_db()
    tg_bot = TG_Bot(user_storage, order_storage)
    await tg_bot.init()
    await tg_bot.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
