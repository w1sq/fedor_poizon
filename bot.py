import typing

import aiogram
import aiohttp
import asyncio
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from db.storage import UserStorage, User, OrderStorage, Order
import aiofiles
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


from config import Config


class GetUserInfo(StatesGroup):
    client_name = State()
    phone = State()
    city = State()
    street = State()
    house = State()
    building = State()
    apartament = State()


class GetProductInfo(StatesGroup):
    link = State()
    size = State()
    price = State()


class GetOrderSendingConfirm(StatesGroup):
    answer = State()


class TG_Bot:
    def __init__(self, user_storage: UserStorage, order_storage: OrderStorage):
        self._user_storage: UserStorage = user_storage
        self._order_storage: OrderStorage = order_storage
        self._bot: aiogram.Bot = aiogram.Bot(token=Config.TGBOT_API_KEY)
        self._storage: MemoryStorage = MemoryStorage()
        self._dispatcher: aiogram.Dispatcher = aiogram.Dispatcher(
            self._bot, storage=self._storage
        )
        self._create_keyboards()

    async def init(self):
        self._init_handler()

    async def start(self):
        print("Bot has started")
        await self._dispatcher.start_polling()

    async def get_last_rate(self) -> float:
        rate = None
        while not rate:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.cbr-xml-daily.ru/latest.js"
                ) as response:
                    if response.status == 200:
                        data = await response.json(
                            content_type="application/javascript"
                        )
                        rate = 1 / data["rates"]["CNY"]
            await asyncio.sleep(5)
        return rate

    async def _show_menu(self, message: aiogram.types.Message):
        user = await self._user_storage.get_by_id(message.chat.id)
        if user and user.full_name:
            await message.answer(
                "Меню <a href='https://t.me/freshshshsh'>магазина T & Z Express</a>",
                parse_mode="HTML",
                reply_markup=self._inline_menu_keyboard,
                # disable_web_page_preview=True,
            )
        else:
            await message.answer(
                "Меню <a href='https://t.me/freshshshsh'>магазина T & Z Express</a>\n\nСейчас Вы не зарегестрированы, поэтому Оформление заказа и Корзина Вам не доступны, пройдите регистрацию, нажав кнопку ниже:",
                parse_mode="HTML",
                reply_markup=self._inline_reg_keyboard,
                # disable_web_page_preview=True,
            )

    async def _referal_system(self, message: aiogram.types.Message):
        user = await self._user_storage.get_by_id(message.chat.id)
        withdraw_keyboard = InlineKeyboardMarkup().row(
            InlineKeyboardButton("Вывести", callback_data=f"withdraw {user.id}")
        )
        await message.answer(
            f"Ваш баланс: <b>{user.balance} ₽</b>\n\nПригласите друга и заработайте 20% от прибыли!\nВаша реферальная ссылка:\n\nhttps://t.me/fedoreventqrbot?start={user.id}",
            parse_mode="HTML",
            reply_markup=withdraw_keyboard,
        )

    async def _withdraw_balance(self, call: aiogram.types.CallbackQuery):
        user_id = int(call.data.split()[1])
        user = await self._user_storage.get_by_id(user_id)
        if user and user.balance > 1000:
            await call.message.answer("С вами свяжется менеджер.")
        else:
            await call.message.answer("Вывод доступен от 1000 ₽ на балансе.")

    async def _show_cart(self, call: aiogram.types.CallbackQuery):
        user_orders = await self._order_storage.get_orders_by_user_id(
            call.message.chat.id
        )
        if user_orders:
            await call.message.answer("🛒 Ваша корзина:")
            for order in user_orders:
                delete_keyboard = InlineKeyboardMarkup().row(
                    InlineKeyboardButton(
                        text="❌ Удалить", callback_data=f"delete_order {order.id}"
                    )
                )
                await call.message.answer(str(order), reply_markup=delete_keyboard)
        else:
            await call.message.answer("В вашей корзине нет ни одного товара")

    async def _delete_product(self, call: aiogram.types.CallbackQuery):
        order_id = int(call.data.split()[1])
        await self._order_storage.delete(order_id)
        await call.answer("✅ Вы успешно удалили товар")
        await call.message.edit_text(
            "<strike>" + call.message.text + "</strike>", parse_mode="HTML"
        )

    async def _send_order(self, call: aiogram.types.CallbackQuery):
        user_orders = await self._order_storage.get_orders_by_user_id(
            call.message.chat.id
        )
        if user_orders:
            await call.message.answer(
                "Ваш заказ:", reply_markup=self._order_sending_keyboard
            )
            for order in user_orders:
                await call.message.answer(str(order))
            await GetOrderSendingConfirm.answer.set()
        else:
            await call.message.answer(
                "Чтобы отправить заказ - нужно чтобы у вас было что-то в корзине. Сейчас там пусто."
            )

    async def _process_order_sending_answer(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        user = await self._user_storage.get_by_id(message.from_user.id)
        if message.text.strip() == "✅ Подтверждаю":
            await self._bot.send_message(
                917865313,
                # 5546230210,
                f"""❗️Новая заявка❗️\n\nПользователь <a href="tg://user?id={user.id}">{user.full_name}</a>\nC id: {user.id}\n\nНомер телефона: {user.phone}\n\nАдрес доставки:\n\tГород: {user.city}\n\tУлица: {user.street}\n\tДом: {user.house}\n\tКорпус: {user.building}\n\tКвартира: {user.apartament}""",
                parse_mode="HTML",
            )
            user_orders = await self._order_storage.get_orders_by_user_id(
                message.from_user.id
            )
            total_price = 0
            for order in user_orders:
                await self._bot.send_message(
                    917865313,
                    # 5546230210,
                    str(order),
                )
                total_price += order.price
                await self._order_storage.delete(order.id)
            await self._bot.send_chat_action(
                chat_id=message.from_user.id, action=aiogram.types.ChatActions.TYPING
            )
            total_price = round(
                1.06 * total_price * (await self.get_last_rate()) + 1000
            )
            await self._bot.send_message(
                917865313,
                # 5546230210,
                f"Приблизительная цена заказа в рублях: {total_price} ₽",
            )
            await message.answer(
                f"С вами скоро свяжется наш оператор, ожидайте обратной связи.\n\nПриблизительная цена заказа в рублях: {total_price} ₽",
                reply_markup=self._menu_keyboard_user,
            )
            await state.finish()
        elif message.text.strip() == "Назад":
            await state.finish()
            await self._show_menu(message=message)
        else:
            await message.answer(
                "Нет такого варианта ответа", reply_markup=self._order_sending_keyboard
            )

    async def _ask_order_type(self, call: aiogram.types.CallbackQuery):
        await call.message.answer(
            "Выберите тип нужного товара(желательно максимально полное):",
            reply_markup=self._order_type_keyboard,
        )

    async def _start_user_registration(self, call: aiogram.types.CallbackQuery):
        await call.message.answer(
            "Давайте сначала заполним немного информации о себе(исключительно данные для доставки)\n\n1/7 Введите Ваше полное имя и фамилию:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.client_name.set()

    async def _ask_product_name(self, call: aiogram.types.CallbackQuery):
        product_type = call.data.split()[1]
        await GetProductInfo.link.set()
        state = self._dispatcher.get_current().current_state()
        await state.update_data(product_type=product_type)
        levels = "3"
        if product_type in ("onesize", "tech"):
            levels = "2"
        await state.update_data(levels=levels)
        async with aiofiles.open("link.jpg", "rb") as link_pic:
            await call.message.answer_photo(
                link_pic,
                f"1/{levels} Пришлите ссылку на товар:",
                reply_markup=self._cancel_keyboard,
            )

    async def _process_product_name(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(product_link=message.text.strip())
        if state_data["product_type"] in ("onesize", "tech"):
            async with aiofiles.open("pic.jpg", "rb") as picture:
                await message.answer_photo(
                    picture,
                    f"2/{state_data['levels']}  Введите стоимость товара в юанях (зачеркнутая цена):",
                    reply_markup=self._cancel_keyboard,
                )
            await GetProductInfo.price.set()
        else:
            await message.answer(
                f"2/{state_data['levels']} Введите нужный размер:",
                reply_markup=self._cancel_keyboard,
            )
            await GetProductInfo.size.set()

    async def _process_product_size(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(product_size=message.text.strip())
        async with aiofiles.open("pic.jpg", "rb") as picture:
            await message.answer_photo(
                picture,
                f"3/{state_data['levels']} Введите стоимость товара в юанях (зачеркнутая цена):",
                reply_markup=self._cancel_keyboard,
            )
        await GetProductInfo.price.set()

    async def _process_product_price(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        if message.text.strip().isdigit():
            state_data = await state.get_data()
            product_price = int(message.text.strip())
            product_size = state_data.get("product_size", "one size")
            order = Order(
                buyer_id=message.from_user.id,
                link=state_data["product_link"],
                size=product_size,
                price=product_price,
            )
            await self._order_storage.create(order)
            await message.answer(
                "✅ Вы успешно добавили новый товар в свою корзину:",
                reply_markup=self._inline_menu_keyboard,
            )
            await message.answer(str(order))
            await state.finish()
        else:
            await message.answer("Введите только число юаней(цифрами):")

    async def _process_client_name(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_name=message.text.strip())
        await message.answer(
            "2/7 Введите Ваш номер телефона:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.phone.set()

    async def _process_client_phone(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_phone=message.text.strip())
        await message.answer(
            "3/7 Введите город доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.city.set()

    async def _process_client_city(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_city=message.text.strip())
        await message.answer(
            "4/7 Введите название улицы для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.street.set()

    async def _process_client_street(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_street=message.text.strip())
        await message.answer(
            "5/7 Введите номер дома для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.house.set()

    async def _process_client_house(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_house=message.text.strip())
        await message.answer(
            "6/7 Введите номер подъезда для доставки, если нет - смело пишите нет:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.building.set()

    async def _process_client_building(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_building=message.text.strip())
        await message.answer(
            "7/7 Введите номер квартиры/офиса для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.apartament.set()

    async def _process_client_apartament(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        db_user = await self._user_storage.get_by_id(message.from_user.id)
        db_user.full_name = state_data["client_name"]
        db_user.phone = state_data["client_phone"]
        db_user.city = state_data["client_city"]
        db_user.street = state_data["client_street"]
        db_user.house = state_data["client_house"]
        db_user.building = state_data["client_building"]
        db_user.apartament = message.text.strip()
        await state.finish()
        await self._user_storage.update(db_user)
        await message.answer(
            "✅ Вы успешно заполнили все необходимые данные, теперь вы можете добавлять товары в корзину и оформлять заказы.",
            reply_markup=self._inline_menu_keyboard,
        )

    async def _cancel_handler(
        self, call: aiogram.types.CallbackQuery, state: aiogram.dispatcher.FSMContext
    ):
        current_state = await state.get_state()
        if current_state is not None:
            await state.finish()
        await self._bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id
        )
        await self._show_menu(call.message)

    def _init_handler(self):
        self._dispatcher.register_message_handler(
            self._user_middleware(self._show_menu),
            text="Меню",
        )

        self._dispatcher.register_message_handler(
            self._user_middleware(self._referal_system),
            text="💸 Реферальная система",
        )
        self._dispatcher.register_message_handler(
            self._user_middleware(self._show_menu),
            commands=["start", "menu"],
        )
        self._dispatcher.register_callback_query_handler(
            self._start_user_registration,
            aiogram.dispatcher.filters.Text(startswith="registration"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._ask_order_type,
            aiogram.dispatcher.filters.Text(startswith="add_product"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._show_cart,
            aiogram.dispatcher.filters.Text(startswith="cart"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._delete_product,
            aiogram.dispatcher.filters.Text(startswith="delete_order"),
        )
        self._dispatcher.register_callback_query_handler(
            self._send_order,
            aiogram.dispatcher.filters.Text(startswith="send_order"),
            state="*",
        )
        self._dispatcher.register_message_handler(
            self._process_order_sending_answer, state=GetOrderSendingConfirm.answer
        )

        self._dispatcher.register_callback_query_handler(
            self._ask_product_name,
            aiogram.dispatcher.filters.Text(startswith="type"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._cancel_handler,
            aiogram.dispatcher.filters.Text(startswith="cancel"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._withdraw_balance,
            aiogram.dispatcher.filters.Text(startswith="withdraw"),
            state="*",
        )
        self._dispatcher.register_message_handler(
            self._process_product_name, state=GetProductInfo.link
        )
        self._dispatcher.register_message_handler(
            self._process_product_size, state=GetProductInfo.size
        )
        self._dispatcher.register_message_handler(
            self._process_product_price, state=GetProductInfo.price
        )
        self._dispatcher.register_message_handler(
            self._process_client_name, state=GetUserInfo.client_name
        )
        self._dispatcher.register_message_handler(
            self._process_client_phone, state=GetUserInfo.phone
        )
        self._dispatcher.register_message_handler(
            self._process_client_city, state=GetUserInfo.city
        )
        self._dispatcher.register_message_handler(
            self._process_client_street, state=GetUserInfo.street
        )
        self._dispatcher.register_message_handler(
            self._process_client_house, state=GetUserInfo.house
        )
        self._dispatcher.register_message_handler(
            self._process_client_building, state=GetUserInfo.building
        )
        self._dispatcher.register_message_handler(
            self._process_client_apartament, state=GetUserInfo.apartament
        )

    def _user_middleware(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, *args, **kwargs):
            user = await self._user_storage.get_by_id(message.chat.id)
            if user is None:
                split_message = message.text.split()
                if (
                    len(split_message) == 2
                    and split_message[1].isdigit()
                    and await self._user_storage.get_by_id(int(split_message[1]))
                ):
                    inviter_id = int(split_message[1])
                    await self._bot.send_message(
                        chat_id=inviter_id, text="❤️ Спасибо за приглашённого друга."
                    )
                    user = User(
                        id=message.chat.id, role=User.USER, inviter_id=inviter_id
                    )
                    await message.answer("✅ Вы успешно установили своего пригласителя")
                else:
                    user = User(id=message.chat.id, role=User.USER)
                await self._user_storage.create(user)
            if user.role != User.BLOCKED:
                await func(message)

        return wrapper

    def _admin_required(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, user: User, *args, **kwargs):
            if user.role == User.ADMIN:
                await func(message, user)

        return wrapper

    def _create_keyboards(self):
        self._menu_keyboard_user = ReplyKeyboardMarkup(resize_keyboard=True).row(
            KeyboardButton("Меню"), KeyboardButton("💸 Реферальная система")
        )

        self._order_sending_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(
            KeyboardButton("✅ Подтверждаю"), KeyboardButton("Назад")
        )

        self._inline_menu_keyboard = (
            InlineKeyboardMarkup()
            .row(InlineKeyboardButton("Добавить товар", callback_data="add_product"))
            .row(InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
            .row(InlineKeyboardButton("Оформить заказ", callback_data="send_order"))
            .row(
                InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/clover4th"
                )
            )
        )

        self._inline_reg_keyboard = (
            InlineKeyboardMarkup()
            .row(
                InlineKeyboardButton("Зарегестрироваться", callback_data="registration")
            )
            .row(
                InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/clover4th"
                )
            )
        )

        self._order_type_keyboard = (
            InlineKeyboardMarkup()
            .row(
                InlineKeyboardButton(
                    text="👟 Летняя обувь ", callback_data="type sneakers"
                )
            )
            .row(
                InlineKeyboardButton(text="🥾 Зимняя обувь", callback_data="type boots")
            )
            .row(
                InlineKeyboardButton(
                    text="👕 Майки / Рубашки / Толстовки", callback_data="type top"
                )
            )
            .row(
                InlineKeyboardButton(
                    text="👖 Штаны / Джинсы / Брюки", callback_data="type bottom"
                )
            )
            .row(InlineKeyboardButton(text="💻 Техника", callback_data="type tech"))
            .row(InlineKeyboardButton(text="👜 One size", callback_data="type onesize"))
        )
        self._cancel_keyboard = InlineKeyboardMarkup().row(
            InlineKeyboardButton(text="Отмена", callback_data="cancel")
        )
