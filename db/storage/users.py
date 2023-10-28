from db.db import DB
from typing import List
from dataclasses import dataclass


@dataclass
class User:
    ADMIN = "admin"
    USER = "user"
    BLOCKED = "blocked"

    id: int
    role: str
    full_name: str = None
    phone: str = None
    address: str = None
    balance: int = 0
    inviter_id: int = None


class UserStorage:
    __table = "users"

    def __init__(self, db: DB):
        self._db = db

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id BIGINT PRIMARY KEY,
                role TEXT,
                full_name TEXT DEFAULT NULL,
                phone TEXT DEFAULT NULL,
                address TEXT DEFAULT NULL,
                balance INT NOT NULL DEFAULT 0,
                inviter_id BIGINT DEFAULT NULL
            )
        """
        )

    async def get_by_id(self, user_id: int) -> User | None:
        data = await self._db.fetchrow(
            f"SELECT * FROM {self.__table} WHERE id = $1", user_id
        )
        if data is None:
            return None
        return User(
            data[0],
            data[1],
            data[2],
            data[3],
            data[4],
            data[5],
            data[6],
        )

    async def promote_to_admin(self, id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.ADMIN, id
        )

    async def demote_from_admin(self, id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.USER, id
        )

    async def get_role_list(self, role: str) -> List[int] | None:
        roles = await self._db.fetch(
            f"SELECT * FROM {self.__table} WHERE role = $1", role
        )
        if roles is None:
            return None
        return [role[0] for role in roles]

    async def create(self, user: User):
        await self._db.execute(
            f"""
            INSERT INTO {self.__table} (id, role, full_name, phone, address, balance, inviter_id) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            user.id,
            user.role,
            user.full_name,
            user.phone,
            user.address,
            user.balance,
            user.inviter_id,
        )

    async def update(self, user: User):
        await self._db.execute(
            f"""
            UPDATE {self.__table} SET (role, full_name, phone, address, balance, inviter_id) = ($1, $2, $3, $4, $5, $6) WHERE id = $7
        """,
            user.role,
            user.full_name,
            user.phone,
            user.address,
            user.balance,
            user.inviter_id,
            user.id,
        )

    async def get_all_members(self) -> List[User] | None:
        data = await self._db.fetch(
            f"""
            SELECT * FROM {self.__table}
        """
        )
        if data is None:
            return None
        return [
            User(
                user_data[0],
                user_data[1],
                user_data[2],
                user_data[3],
                user_data[4],
                user_data[5],
                user_data[6],
            )
            for user_data in data
        ]

    async def give_bonus(self, user_id: int, bonus: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET balance = balance + $1 WHERE id = $2",
            bonus,
            user_id,
        )

    async def get_user_amount(self) -> int:
        return await self._db.fetchval(f"SELECT COUNT(*) FROM {self.__table}")

    async def ban_user(self, user_id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.BLOCKED, user_id
        )

    async def unban_user(self, user_id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.USER, user_id
        )

    async def delete(self, user_id: int):
        await self._db.execute(
            f"""
            DELETE FROM {self.__table} WHERE id = $1
        """,
            user_id,
        )
