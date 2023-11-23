from db.db import DB
from typing import List
from dataclasses import dataclass


@dataclass
class Order:
    buyer_id: int
    link: str
    price: int
    size: str = "one size"
    id: int = None

    def custom_str(self, yuan_rate: float) -> str:
        rub_price = round(1.05 * 1.05 * self.price * yuan_rate + 1000)
        return f"{self.link}\nРазмер: {self.size}\nЦена в юанях: {self.price}\nЦена в рублях: {rub_price}"


class OrderStorage:
    __table = "orders"

    def __init__(self, db: DB):
        self._db = db

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id SERIAL PRIMARY KEY,
                buyer_id BIGINT,
                link TEXT,
                size TEXT NOT NULL DEFAULT 'one size',
                price INT,
                FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """
        )

    async def get_by_id(self, order_id: int) -> Order | None:
        data = await self._db.fetchrow(
            f"SELECT * FROM {self.__table} WHERE id = $1", order_id
        )
        if data is None:
            return None
        return Order(
            id=data[0], buyer_id=data[1], link=data[2], size=data[3], price=data[4]
        )

    async def get_orders_by_user_id(self, user_id: int) -> List[Order] | None:
        data = await self._db.fetch(
            f"SELECT * FROM {self.__table} WHERE buyer_id = $1", user_id
        )
        if data is None:
            return None
        return [
            Order(
                id=order_data[0],
                buyer_id=order_data[1],
                link=order_data[2],
                size=order_data[3],
                price=order_data[4],
            )
            for order_data in data
        ]

    async def create(self, order: Order):
        await self._db.execute(
            f"""
            INSERT INTO {self.__table} (buyer_id, link, size, price) VALUES ($1, $2, $3, $4)
        """,
            order.buyer_id,
            order.link,
            order.size,
            order.price,
        )

    async def get_all_members(self) -> List[Order] | None:
        data = await self._db.fetch(
            f"""
            SELECT * FROM {self.__table}
        """
        )
        if data is None:
            return None
        return [
            Order(
                id=order_data[0],
                buyer_id=order_data[1],
                link=order_data[2],
                size=order_data[3],
                price=order_data[4],
            )
            for order_data in data
        ]

    async def get_orders_amount(self) -> int:
        return await self._db.fetchval(f"SELECT COUNT(*) FROM {self.__table}")

    async def delete(self, order_id: int):
        await self._db.execute(
            f"""
            DELETE FROM {self.__table} WHERE id = $1
        """,
            order_id,
        )
