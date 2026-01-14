import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

MAIN_BOT_TOKEN = "8563807556:AAEjUX7i4gGCBV97SVNGeZV83fwsj7o8cZU"

dp = Dispatcher()

spam_tasks = {}  # token -> asyncio.Task


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Сервис-бот управления другими ботами\n\n"
        "Команды:\n"
        "/info <TOKEN>\n"
        "/send <TOKEN> <CHAT_ID> <TEXT>\n"
        "/spam <TOKEN> <CHAT_ID> <TEXT>\n"
        "/stop <TOKEN>"
    )


@dp.message(Command("info"))
async def info(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование:\n/info <TOKEN>")
        return

    token = args[1]

    try:
        bot = Bot(token)
        me = await bot.get_me()
        await message.answer(
            f"ID: {me.id}\n"
            f"Username: @{me.username}\n"
            f"Name: {me.first_name}"
        )
    except Exception as e:
        await message.answer(f"Ошибка:\n{e}")


@dp.message(Command("send"))
async def send(message: Message):
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.answer("Использование:\n/send <TOKEN> <CHAT_ID> <TEXT>")
        return

    token, chat_id, text = args[1], args[2], args[3]

    try:
        bot = Bot(token)
        await bot.send_message(chat_id, text)
        await message.answer("Сообщение отправлено")
    except Exception as e:
        await message.answer(f"Ошибка отправки:\n{e}")


async def spam_loop(token: str, chat_id: str, text: str):
    bot = Bot(token)
    while True:
        try:
            await bot.send_message(chat_id, text)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"SPAM ERROR ({token}):", e)
            await asyncio.sleep(2)


@dp.message(Command("spam"))
async def spam(message: Message):
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.answer("Использование:\n/spam <TOKEN> <CHAT_ID> <TEXT>")
        return

    token, chat_id, text = args[1], args[2], args[3]

    if token in spam_tasks:
        await message.answer("Для этого токена рассылка уже запущена")
        return

    task = asyncio.create_task(spam_loop(token, chat_id, text))
    spam_tasks[token] = task

    await message.answer("Бесконечная рассылка запущена (0.5 сек)")


@dp.message(Command("stop"))
async def stop(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование:\n/stop <TOKEN>")
        return

    token = args[1]

    task = spam_tasks.pop(token, None)
    if task:
        task.cancel()
        await message.answer("Рассылка остановлена")
    else:
        await message.answer("Для этого токена рассылка не запущена")


async def main():
    bot = Bot(MAIN_BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
