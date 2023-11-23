import typing

import aiogram
import aiohttp
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
    address = State()


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
        self._yuan_rate = None
        self._photo = None
        self._create_keyboards()

    async def init(self):
        await self._get_last_rate()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self._get_last_rate, "interval", minutes=1)
        scheduler.start()
        self._init_handler()

    async def start(self):
        print("Bot has started")
        await self._dispatcher.start_polling()

    async def _get_last_rate(self):
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
        self._yuan_rate = rate

    async def _show_menu(self, message: aiogram.types.Message):
        if not self._photo:
            photo = aiogram.types.InputFile("logo.jpg")
        else:
            photo = self._photo
        sent_message = await message.answer_photo(
            photo,
            caption="Меню <a href='https://t.me/marequstore'>MAREQU Store</a>",
            parse_mode="HTML",
            reply_markup=self._inline_menu_keyboard,
            # disable_web_page_preview=True,
        )
        self._photo = sent_message.photo[0].file_id

    async def _referal_system(self, call: aiogram.types.CallbackQuery):
        user = await self._user_storage.get_by_id(call.message.chat.id)
        withdraw_keyboard = InlineKeyboardMarkup().row(
            InlineKeyboardButton("Вывести", callback_data=f"withdraw {user.id}")
        )
        await call.message.answer(
            f"Ваш баланс: <b>{user.balance} ₽</b>\n\nПригласите друга и заработайте 20% от прибыли!\nВаша реферальная ссылка:\n\nhttps://t.me/marequbot?start={user.id}",
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
            await call.message.answer(
                "Проверьте, не забыли ли Вы ничего 🤔\n🛒 Ваша корзина:",
                reply_markup=self._inline_cart_keyboard,
            )
            for order in user_orders:
                delete_keyboard = InlineKeyboardMarkup().row(
                    InlineKeyboardButton(
                        text="❌ Удалить", callback_data=f"delete_order {order.id}"
                    )
                )
                await call.message.answer(
                    order.custom_str(self._yuan_rate),
                    reply_markup=delete_keyboard,
                )
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
        user = await self._user_storage.get_by_id(call.message.chat.id)
        if user and user.full_name:
            user_orders = await self._order_storage.get_orders_by_user_id(
                call.message.chat.id
            )
            if user_orders:
                await call.message.answer(
                    "Убедитесь, что все данные верны 😊\n🛒 Ваш заказ:",
                    reply_markup=self._order_sending_keyboard,
                )
                for order in user_orders:
                    await call.message.answer(order.custom_str(self._yuan_rate))
                await GetOrderSendingConfirm.answer.set()
            else:
                await call.message.answer(
                    "Чтобы отправить заказ - нужно чтобы у вас было что-то в корзине. Сейчас там пусто."
                )
        else:
            await call.message.answer(
                "Сейчас Вы не зарегестрированы, поэтому Оформление заказа Вам не доступно, пройдите регистрацию, нажав кнопку ниже:",
                parse_mode="HTML",
                reply_markup=self._inline_reg_keyboard,
                # disable_web_page_preview=True,
            )

    async def _process_order_sending_answer(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        user = await self._user_storage.get_by_id(message.from_user.id)
        if message.text.strip() == "✅ Подтверждаю":
            await self._bot.send_message(
                917865313,
                # 5546230210,
                f"""❗️Новая заявка❗️\n\nПользователь <a href="tg://user?id={user.id}">{user.full_name}</a>\nC id: {user.id}\n\nНомер телефона: {user.phone}\n\nАдрес доставки: {user.address}""",
                parse_mode="HTML",
            )
            user_orders = await self._order_storage.get_orders_by_user_id(
                message.from_user.id
            )
            await self._bot.send_chat_action(
                chat_id=message.from_user.id, action=aiogram.types.ChatActions.TYPING
            )
            total_price_yuan = 0
            total_price_rub = 0
            for order in user_orders:
                rub_price = round(1.05 * 1.05 * order.price * self._yuan_rate + 1000)
                give_bonuses_keyboard = None
                if user.inviter_id:
                    bonus_from_order = round(
                        1.05 * 0.05 * order.price * self._yuan_rate * 0.2
                    )
                    give_bonuses_keyboard = InlineKeyboardMarkup().row(
                        InlineKeyboardButton(
                            "Выдать бонусы",
                            callback_data=f"give_bonus {user.inviter_id} {bonus_from_order}",
                        )
                    )
                await self._bot.send_message(
                    917865313,
                    # 5546230210,
                    order.custom_str(self._yuan_rate),
                    reply_markup=give_bonuses_keyboard,
                )
                total_price_yuan += order.price
                total_price_rub += rub_price
                await self._order_storage.delete(order.id)

            total_profit = round(1.05 * 0.05 * total_price_yuan * self._yuan_rate)
            await self._bot.send_message(
                917865313,
                # 5546230210,
                f"Приблизительная цена заказа в рублях: {total_price_rub} ₽\nПриблизительная прибыль заказа в рублях: {total_profit} ₽",
            )
            await message.answer(
                f"Оператор уже работает над заказом и скоро с Вами свяжется. Спасибо, что вы с нами ❤️\n\n💰Итоговая стоимость {total_price_rub} руб с доставкой до склада в Москве.\n\n🚚 Доставка СДЭКом от склада в Москве по России оплачивается отдельно",
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

    async def _give_bonus(self, call: aiogram.types.CallbackQuery):
        user_id, bonus = list(map(int, call.data.split()[1:]))
        await call.message.edit_reply_markup()
        await self._user_storage.give_bonus(user_id, bonus)
        await call.message.answer(
            f"Успешно выдано <a href='tg://user?id={user_id}'>пользователю</a> {bonus} бонусов",
            parse_mode="HTML",
        )
        await self._bot.send_message(
            user_id,
            f"Поздравляем 🎉 \nВы получили {bonus} бонусов за заказ друга 🤝\nСпасибо, что советуете наш сервис друзьям ❤️\n1 бонус = 1 рубль\nВы можете потратить бонусы у нас или вывести их на свою карту 🙂\n\n( для уточнения деталей реферальной программы обратитесь к менеджеру )",
        )

    async def _ask_order_type(self, call: aiogram.types.CallbackQuery):
        await call.message.answer(
            "👀 Выберите тип интересующего товара:",
            reply_markup=self._order_type_keyboard,
        )

    async def _start_user_registration(self, call: aiogram.types.CallbackQuery):
        await call.message.answer(
            "Давайте сначала заполним немного информации о себе(исключительно данные для доставки)\n\n1/3 Введите Ваше полное имя и фамилию:\n\nЕсли вы не хотите указывать данные сразу, то напишите «-»",
            # reply_markup=self._cancel_keyboard,
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
                f"<a href='https://telegra.ph/Kak-skachat-Poison-i-najti-tam-tovar-10-27'>Как заказать товар?</a> - ссылка\n1/{levels} Пришлите ссылку на товар по инструкции на картинке:",
                # reply_markup=self._cancel_keyboard,
                parse_mode="HTML",
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
                    f"2/{state_data['levels']} Введите стоимость товара в юанях (зачеркнутая цена):",
                    # reply_markup=self._cancel_keyboard,
                )
            await GetProductInfo.price.set()
        else:
            await message.answer(
                f"2/{state_data['levels']} Введите нужный размер:",
                # reply_markup=self._cancel_keyboard,
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
                # reply_markup=self._cancel_keyboard,
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
                "✅ Вы успешно добавили новый товар в корзину:",
                reply_markup=self._inline_menu_keyboard,
            )
            await message.answer(order.custom_str(self._yuan_rate))
            await state.finish()
        else:
            await message.answer("Введите только число юаней(цифрами):")

    async def _process_client_name(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        if message.text.strip() == "-":
            await message.answer(
                "Вы пропустили регистрацию, но перед оформлением заказа зарегестрироваться будет необходимо."
            )
            await state.finish()
            await self._show_menu(message)
        else:
            await state.update_data(client_name=message.text.strip())
            await message.answer(
                "2/3 Введите Ваш номер телефона:",
                # reply_markup=self._cancel_keyboard,
            )
            await GetUserInfo.phone.set()

    async def _process_client_phone(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        await state.update_data(client_phone=message.text.strip())
        await message.answer(
            "3/3 Введите адрес доставки:",
            # reply_markup=self._cancel_keyboard,
        )
        await GetUserInfo.address.set()

    async def _process_client_address(
        self, message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext
    ):
        state_data = await state.get_data()
        db_user = await self._user_storage.get_by_id(message.from_user.id)
        db_user.full_name = state_data["client_name"]
        db_user.phone = state_data["client_phone"]
        db_user.address = message.text.strip()
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
        self._dispatcher.register_callback_query_handler(
            self._give_bonus,
            aiogram.dispatcher.filters.Text(startswith="give_bonus"),
            state="*",
        )
        self._dispatcher.register_callback_query_handler(
            self._referal_system,
            aiogram.dispatcher.filters.Text(startswith="referal_system"),
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
            self._process_client_address, state=GetUserInfo.address
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
                await message.answer(
                    "Сейчас Вы не зарегестрированы, поэтому Оформление заказа Вам не доступно, пройдите регистрацию, нажав кнопку ниже:",
                    parse_mode="HTML",
                    reply_markup=self._inline_reg_keyboard,
                    # disable_web_page_preview=True,
                )
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
            KeyboardButton("Меню")
        )

        self._order_sending_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(
            KeyboardButton("✅ Подтверждаю"), KeyboardButton("Назад")
        )

        self._inline_cart_keyboard = (
            InlineKeyboardMarkup()
            .row(InlineKeyboardButton("😎 Добавить товар", callback_data="add_product"))
            .row(InlineKeyboardButton("✅ Оформить заказ", callback_data="send_order"))
            .row(
                InlineKeyboardButton(
                    "📞 Связаться с менеджером", url="https://t.me/clover4th"
                )
            )
        )

        self._inline_menu_keyboard = (
            InlineKeyboardMarkup()
            .row(InlineKeyboardButton("😎 Добавить товар", callback_data="add_product"))
            .row(InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
            .row(
                InlineKeyboardButton("✅ Подтвердить заказ", callback_data="send_order")
            )
            .row(
                InlineKeyboardButton(
                    "📞 Связаться с менеджером", url="https://t.me/clover4th"
                )
            )
            .row(
                InlineKeyboardButton(
                    "💸 Реферальная система", callback_data="referal_system"
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
                    "📞 Связаться с менеджером", url="https://t.me/clover4th"
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
            .row(
                InlineKeyboardButton(
                    text="«🧥 Куртки / Верхняя одежда»", callback_data="type jacket"
                )
            )
            .row(InlineKeyboardButton(text="💻 Техника", callback_data="type tech"))
            .row(
                InlineKeyboardButton(
                    text="👜 Аксессуары / Сумки / Рюкзаки", callback_data="type onesize"
                )
            )
        )
        # self._cancel_keyboard = InlineKeyboardMarkup().row(
        #     InlineKeyboardButton(text="Отмена", callback_data="cancel")
        # )
