import typing

import aiogram
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from db.storage import UserStorage, User
import aiofiles
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


from config import Config


class GetProductInfo(StatesGroup):
    product_name = State()
    size = State()
    price = State()
    client_name = State()
    phone = State()
    city = State()
    street = State()
    house = State()
    building = State()
    apartment = State()


class TG_Bot:
    def __init__(self, user_storage: UserStorage):
        self._user_storage: UserStorage = user_storage
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

    async def _show_menu(self, message: aiogram.types.Message, user: User):
        await message.answer(
            "Меню <a href='https://t.me/freshshshsh'>магазина T & Z Express</a>",
            parse_mode="HTML",
            reply_markup=self._inline_menu_keyboard,
            # disable_web_page_preview=True,
        )

    async def _ask_order_type(self, call: aiogram.types.CallbackQuery):
        await call.message.answer(
            "Выберите тип нужного товара(желательно максимально полное):",
            reply_markup=self._order_type_keyboard,
        )

    async def _ask_product_name(self, call: aiogram.types.CallbackQuery):
        product_type = call.data.split()[1]
        await GetProductInfo.product_name.set()
        state = self._dispatcher.get_current().current_state()
        await state.update_data(product_type=product_type)
        levels = "10"
        if product_type in ("onesize", "tech"):
            levels = "9"
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
        await state.update_data(product_name=message.text.strip())
        if state_data["product_type"] in ("onesize", "tech"):
            async with aiofiles.open("pic.jpg", "rb") as picture:
                await message.answer_photo(
                    picture,
                    f"3/{state_data['levels']}  Введите стоимость товара в юанях (зачеркнутая цена):",
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
        state_data = await state.get_data()
        await state.update_data(product_price=message.text.strip())
        await message.answer(
            f"4/{state_data['levels']} Введите Ваше полное Имя и Фамилию (все данные нужны будут для доставки):",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.client_name.set()

    async def _process_client_name(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_name=message.text.strip())
        await message.answer(
            f"5/{state_data['levels']} Введите Ваш номер телефона:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.phone.set()

    async def _process_client_phone(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_phone=message.text.strip())
        await message.answer(
            f"6/{state_data['levels']} Введите город доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.city.set()

    async def _process_client_city(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_city=message.text.strip())
        await message.answer(
            f"7/{state_data['levels']} Введите название улицы для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.street.set()

    async def _process_client_street(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_street=message.text.strip())
        await message.answer(
            f"8/{state_data['levels']} Введите номер дома для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.house.set()

    async def _process_client_house(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_house=message.text.strip())
        await message.answer(
            f"9/{state_data['levels']} Введите номер подъезда для доставки, если нет - смело пишите нет:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.building.set()

    async def _process_client_building(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        await state.update_data(client_building=message.text.strip())
        await message.answer(
            f"10/{state_data['levels']} Введите номер квартиры/офиса для доставки:",
            reply_markup=self._cancel_keyboard,
        )
        await GetProductInfo.apartment.set()

    async def _process_client_apartament(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        product_size = state_data.get("product_size", "")
        size_info = ""
        if product_size:
            size_info = "\n\nРазмер: " + product_size
        await self._bot.send_message(
            917865313,
            f"""❗️Новая заявка❗️\n\nПользователь: <a href="tg://user?id={message.from_user.id}">{state_data["client_name"]}</a> с id: {message.from_user.id}\n\nТовар: {state_data["product_name"]}\n\nТип: {state_data["product_type"]}{size_info}\n\nСтоимость: {state_data["product_price"]} юаней\n\nНомер телефона: {state_data["client_phone"]}\n\nАдрес доставки:\n\tГород: {state_data["client_city"]}\n\tУлица: {state_data["client_street"]}\n\tДом: {state_data["client_house"]}\n\tКорпус: {state_data["client_building"]}\n\tКвартира: {message.text}""",
            parse_mode="HTML",
        )
        await message.answer(
            "С вами скоро свяжется наш оператор, ожидайте обратной связи.",
            reply_markup=self._menu_keyboard_user,
        )
        await state.finish()

    async def _cancel_handler(
        self, call: aiogram.types.CallbackQuery, state: aiogram.dispatcher.FSMContext
    ):
        current_state = await state.get_state()
        if current_state is not None:
            await state.finish()
        await self._bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id
        )
        await self._show_menu(
            call.message, await self._user_storage.get_by_id(call.message.chat.id)
        )

    def _init_handler(self):
        self._dispatcher.register_message_handler(
            self._user_middleware(self._show_menu),
            text="Меню",
        )
        self._dispatcher.register_message_handler(
            self._user_middleware(self._show_menu),
            commands=["start", "menu"],
        )
        self._dispatcher.register_callback_query_handler(
            self._ask_order_type,
            aiogram.dispatcher.filters.Text(startswith="create_order"),
            state="*",
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
        self._dispatcher.register_message_handler(
            self._process_product_name, state=GetProductInfo.product_name
        )
        self._dispatcher.register_message_handler(
            self._process_product_size, state=GetProductInfo.size
        )
        self._dispatcher.register_message_handler(
            self._process_product_price, state=GetProductInfo.price
        )
        self._dispatcher.register_message_handler(
            self._process_client_name, state=GetProductInfo.client_name
        )
        self._dispatcher.register_message_handler(
            self._process_client_phone, state=GetProductInfo.phone
        )
        self._dispatcher.register_message_handler(
            self._process_client_city, state=GetProductInfo.city
        )
        self._dispatcher.register_message_handler(
            self._process_client_street, state=GetProductInfo.street
        )
        self._dispatcher.register_message_handler(
            self._process_client_house, state=GetProductInfo.house
        )
        self._dispatcher.register_message_handler(
            self._process_client_building, state=GetProductInfo.building
        )
        self._dispatcher.register_message_handler(
            self._process_client_apartament, state=GetProductInfo.apartment
        )

    def _user_middleware(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, *args, **kwargs):
            user = await self._user_storage.get_by_id(message.chat.id)
            if user is None:
                user = User(id=message.chat.id, role=User.USER)
                await self._user_storage.create(user)
                await message.answer(
                    "Добро пожаловать!", reply_markup=self._menu_keyboard_user
                )
            if user.role != User.BLOCKED:
                await func(message, user)

        return wrapper

    def _admin_required(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, user: User, *args, **kwargs):
            if user.role == User.ADMIN:
                await func(message, user)

        return wrapper

    def _create_keyboards(self):
        self._menu_keyboard_user = ReplyKeyboardMarkup(resize_keyboard=True).row(
            KeyboardButton("Меню")
        )
        self._inline_menu_keyboard = (
            InlineKeyboardMarkup()
            .row(InlineKeyboardButton("Сделать заказ", callback_data="create_order"))
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
