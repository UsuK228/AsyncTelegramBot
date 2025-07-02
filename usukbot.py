import asyncio
import requests
import logging
import re
import time
import json
import os

from collections import defaultdict
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from bs4 import BeautifulSoup

API_TOKEN = "YOUR TOKEN FROM BOTFATHER"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройки антифлуда
FLOOD_LIMIT = 1  # Максимальное количество сообщений
TIME_LIMIT = 4  # В секундах, за которое нельзя превышать лимит
BAN_TIME = 4  # В секундах, на сколько банить флудера

user_messages = defaultdict(list)
banned_users = {}
USER_DATA_FILE = "user_data.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def log_command(message):
    logger.info(
        f"Command: {message.text} | "
        f"User: {message.from_user.id} | "
        f"Username: @{message.from_user.username} | "
        f"Chat: {message.chat.id} ({message.chat.type})"
    )


class UserBalance:
    def __init__(self):
        self.data = self.load_data()

    @staticmethod
    def load_data():
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_data(self):
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(self.data, f)

    def init_user(self, user_id):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {
                'balance': 500,  # Стартовый баланс
                'activated': True
            }
            self.save_data()

    def get_balance(self, user_id):
        self.init_user(user_id)
        return self.data[str(user_id)]['balance']

    def update_balance(self, user_id, amount):
        self.init_user(user_id)
        self.data[str(user_id)]['balance'] += amount
        self.save_data()
        return self.data[str(user_id)]['balance']

    async def balance_refill_task(self):
        while True:
            await asyncio.sleep(600)  # 10 минут = 600 секунд
            await self.refill_all_balances()

    async def refill_all_balances(self):
        refill_amount = 200
        now = datetime.now()

        for user_id in list(self.data.keys()):
            # Проверяем, когда последний раз пополняли баланс
            last_refill = self.data[user_id].get('last_refill')
            if not last_refill or (now - datetime.fromisoformat(last_refill)) >= timedelta(minutes=10):
                self.data[user_id]['balance'] += refill_amount
                self.data[user_id]['last_refill'] = now.isoformat()

        #        # Отправляем уведомление пользователю
        #        try:
        #            await bot.send_message(
        #                chat_id=int(user_id),
        #                text=f"🔄 Ваш баланс пополнен на {refill_amount}₽ (автоматическое пополнение каждые 10 минут)"
        #            )
        #        except Exception as e:
        #            logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

        self.save_data()
        logger.info(f"Balance automatically refilled, data: {now}")

user_balance = UserBalance()

async def check_flood(message):
    user_id = message.from_user.id

    if user_id in banned_users:
        if datetime.now() < banned_users[user_id]:
            return True
        else:
            del banned_users[user_id]

    user_messages[user_id].append(datetime.now())

    user_messages[user_id] = [
        msg_time for msg_time in user_messages[user_id]
        if datetime.now() - msg_time < timedelta(seconds=TIME_LIMIT)
    ]

    if len(user_messages[user_id]) > FLOOD_LIMIT:
        message.answer("Не флудите!")
        banned_users[user_id] = datetime.now() + timedelta(seconds=BAN_TIME)
        logger.warning(f"User {user_id} (@{message.from_user.username}) banned for flooding for {BAN_TIME} seconds")
        return True

    return False


@dp.message(Command("start"))
async def send_start(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    user_balance.init_user(message.from_user.id)

    await message.reply(f"""
Басуха в деле, {message.from_user.full_name}.
Я - вторая версия мультибота от автора UsuK
(Он начинающий программист, не бейте его!)
Напиши команду /help для более подробной информации
""")


@dp.message(Command("help"))
async def send_help(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    await message.reply("""
Я - вторая версия мультибота от автора UsuK.
Вторая так как первая версия была написана на telebot, эта версия переписана на aiogram (теперь я асинхронен! хз что это значит).
Связаться с создателем можно в Discord: 
Мои текущие команды таковы:
/start -- поздороваться
/help -- информация
/status -- статус своего сервера (онлайн, кол-во игроков...)
/calc [арифметический пример] -- калькулятор
/echo [предложение] -- эхо
/cubic -- кинуть кубик
/oreshnik -- расчет времени полета боевой части баллистической ракеты средней дальности "Орешник" от военного полигона Капустин Яр до Берлина
/myid -- ваш telegram id
/bal -- проверить баланс
/casino [ставка] -- крутануть рулетку
""")

@dp.message(Command("status"))
async def send_status(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    url = "https://gmod-servers.com/server/262471/"

    response = requests.get(url)

    bs = BeautifulSoup(response.text, "lxml")
    players_info = bs.find("tbody")
    serverinfo = players_info.text
    data = serverinfo.split()

    status = data[6]
    count = data[12]
    mapname = data[22]
    checked = data[8]

    if count == "Online":
        count = 0
    if mapname == "Version":
        mapname = "Неизвестно"

    await message.reply(f"""
🔌IP сервера: 95.154.68.79:27015
🟢Статус: {status}
🎮Онлайн: {count}/32
🗺️Карта: {mapname}
🧐Последняя проверка: {checked} мин назад
""")

@dp.message(Command("calc"))
async def send_calc(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    try:
        calc_expr = message.text.split(maxsplit=1)[1]

        if not re.fullmatch(r'^[0-9()+\-*/%]+$', calc_expr):    # цифры, круглые скобки, +, -, /, *, %
            await message.reply("Ошибка: допустимы только числа и операторы")
        else:
            calc_start_time = time.time()
            calc_expr_result = eval(calc_expr)
            calc_end_time = time.time()

            elapsed_time = (calc_end_time - calc_start_time) * 1000 # ответ в миллисек
            await message.reply(f"""
Ответ: {calc_expr_result}
Выполнено за {elapsed_time:.2f} мc
""")
    except Exception as err:
        await message.reply(f"Ошибка: {err}")

@dp.message(Command("echo"))
async def send_echo(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    try:
        if "usuk" in message.text or "усик" in message.text:
            await message.reply("Ошибка: Запрещено писать имя создателя!")
        else:
            await message.reply(message.text.split(maxsplit=1)[1])
    except Exception as err:
        await message.reply(f"Ошибка: {err}")

@dp.message(Command("cubic"))
async def send_cubic(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    cubic_data = await message.reply_dice("🎲")
    cubic_value = cubic_data.dice.value

    await asyncio.sleep(4)
    await message.answer(f"Выпало {cubic_value}!")

@dp.message(Command("oreshnik"))
async def send_oreshnik(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    await message.reply("11-12 минут")
    await asyncio.sleep(1)
    await message.answer("Хохлы пидоры")

@dp.message(Command("myid"))
async def send_myid(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    await message.reply(f"Ваш ID: {message.from_user.id}")

@dp.message(Command("bal"))
async def send_bal(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    bal = user_balance.get_balance(message.from_user.id)
    user_data = user_balance.data.get(str(message.from_user.id), {})
    last_refill = user_data.get('last_refill')

    if last_refill:
        next_refill = datetime.fromisoformat(last_refill) + timedelta(minutes=10)
        time_left = next_refill - datetime.now()
        if time_left.total_seconds() > 0:
            mins, secs = divmod(int(time_left.total_seconds()), 60)
            refill_info = f"\nСледующее пополнение через: {mins} мин {secs} сек"
        else:
            refill_info = "\nПополнение должно произойти в ближайшее время"
    else:
        refill_info = "\nПервое пополнение произойдет в течение 10 минут"

    await message.reply(
        f"Ваш баланс: {bal}"
        f"\nПополнение: +200 каждые 10 минут"
        f"{refill_info}"
    )

@dp.message(Command("casino"))
async def send_casino(message: Message):
    if await check_flood(message):
        return

    log_command(message)

    try:
        podkrut = 45

        bal = user_balance.get_balance(message.from_user.id)
        bet = int(message.text.split(maxsplit=1)[1])
        win = 0

        if bet < 10:
            await message.reply(f"Недостаточная ставка! Минимальная ставка: 10")
            return


        if bal < bet:
            await message.reply(f"Недостаточно средств! Ваш баланс: {bal}")
            return

        user_balance.update_balance(message.from_user.id, -bet)

        casino_data = await message.reply_dice("🎰")
        casino_value = casino_data.dice.value

        await asyncio.sleep(2)
        await message.answer(f"Набрано {casino_value} очков!")
        if casino_value == 64:
            win = bet * 5
            await message.answer(f"Вы выиграли ДЖЕКПОТ ({int(win)})!")
        elif casino_value >= podkrut:
            win = bet * (casino_value / 22)
            await message.answer(f"Вы выиграли {int(win)}!")
        elif casino_value < podkrut:
            await message.answer("Вы проиграли!")

        new_bal = user_balance.update_balance(message.from_user.id, int(win))
        await message.answer(f"Ваш баланс: {new_bal}")
    except Exception as err:
        await message.reply(f"Ошибка {err}")

@dp.message()
async def log_all_messages(message: Message):
    if await check_flood(message):
        return

    logger.info(f"Message: {message.text[:50]} | User: {message.from_user.id} | Username: @{message.from_user.username}")


async def main():
    await dp.start_polling(bot)
    logger.info("Бот запущен и готов к работе!")


if __name__ == "__main__":
    asyncio.run(main())