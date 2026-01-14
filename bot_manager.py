import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Хранилище ботов пользователей
user_bots = {}  # {user_id: {bot_username: token}}
active_spam_tasks = {}  # {user_id: task}

async def get_all_chats(bot_token: str):
    """Получает список всех чатов, где состоит бот"""
    try:
        bot = Bot(token=bot_token)
        chat_ids = set()
        
        # Получаем последние 100 обновлений для нахождения чатов
        try:
            updates = await bot.get_updates(limit=100, offset=-100, timeout=10)
            for update in updates:
                if update.message:
                    chat_ids.add(update.message.chat.id)
                elif update.callback_query and update.callback_query.message:
                    chat_ids.add(update.callback_query.message.chat.id)
                elif update.my_chat_member:
                    chat_ids.add(update.my_chat_member.chat.id)
        except:
            pass  # Игнорируем ошибки при получении обновлений
        
        # Всегда добавляем самого бота (личные сообщения)
        bot_info = await bot.get_me()
        if bot_info.username:
            chat_ids.add(f"@{bot_info.username}")
        
        await bot.session.close()
        return list(chat_ids)
    except Exception as e:
        logger.error(f"Ошибка получения чатов: {e}")
        return []

async def send_to_chat(bot_token: str, chat_id, message_text: str):
    """Отправляет сообщение в конкретный чат"""
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode=ParseMode.HTML
        )
        await bot.session.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки в {chat_id}: {e}")
        return False

async def send_to_all_chats(bot_token: str, message_text: str):
    """Отправляет сообщение во все доступные чаты"""
    try:
        chat_ids = await get_all_chats(bot_token)
        sent = 0
        errors = 0
        
        for chat_id in chat_ids:
            try:
                success = await send_to_chat(bot_token, chat_id, message_text)
                if success:
                    sent += 1
                else:
                    errors += 1
                await asyncio.sleep(0.5)  # Задержка между отправками
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка: {e}")
        
        return sent, errors
    except Exception as e:
        logger.error(f"Ошибка в send_to_all_chats: {e}")
        return 0, 1

# Создаем диспетчер
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    await message.answer(
        "🤖 <b>Бот для массовой рассылки</b>\n\n"
        "<b>Команды:</b>\n"
        "/addbot - добавить бота\n"
        "/send - отправить сообщение всем\n"
        "/spam - бесконечная рассылка\n"
        "/stop - остановить рассылку\n"
        "/list - список ваших ботов",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("addbot"))
async def cmd_addbot(message: types.Message):
    """Добавление бота"""
    await message.answer(
        "🔑 <b>Пришлите токен бота</b>\n\n"
        "Формат: <code>1234567890:ABCdefGHIjklMnOprstUvWxyz</code>\n\n"
        "Получите токен у @BotFather",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda message: ':' in message.text and message.text.split(':')[0].isdigit())
async def process_token(message: types.Message):
    """Обработка токена бота"""
    token = message.text.strip()
    user_id = message.from_user.id
    
    try:
        # Проверяем токен
        temp_bot = Bot(token=token)
        bot_info = await temp_bot.get_me()
        await temp_bot.session.close()
        
        # Сохраняем бота
        if user_id not in user_bots:
            user_bots[user_id] = {}
        
        user_bots[user_id][bot_info.username] = {
            'token': token,
            'name': bot_info.first_name,
            'id': bot_info.id
        }
        
        await message.answer(
            f"✅ <b>Бот успешно добавлен!</b>\n\n"
            f"👤 @{bot_info.username}\n"
            f"📝 {bot_info.first_name}\n"
            f"🆔 <code>{bot_info.id}</code>",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка!</b>\n\n"
            f"Неверный токен или бот не доступен.\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    """Список добавленных ботов"""
    user_id = message.from_user.id
    
    if user_id not in user_bots or not user_bots[user_id]:
        await message.answer("📭 У вас нет добавленных ботов. Используйте /addbot")
        return
    
    bots_list = []
    for username, data in user_bots[user_id].items():
        bots_list.append(f"• @{username} - {data['name']}")
    
    await message.answer(
        "🤖 <b>Ваши боты:</b>\n\n" + "\n".join(bots_list),
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("send"))
async def cmd_send(message: types.Message):
    """Отправка сообщения всем"""
    user_id = message.from_user.id
    
    if user_id not in user_bots or not user_bots[user_id]:
        await message.answer("❌ У вас нет добавленных ботов! Используйте /addbot")
        return
    
    # Просто запрашиваем сообщение
    await message.answer(
        "📝 <b>Введите сообщение для рассылки:</b>\n\n"
        "Оно будет отправлено от имени всех ваших ботов.",
        parse_mode=ParseMode.HTML
    )

async def spam_task(user_id: int, message_text: str):
    """Задача бесконечной рассылки"""
    while True:
        try:
            for username, bot_data in user_bots.get(user_id, {}).items():
                token = bot_data['token']
                sent, errors = await send_to_all_chats(token, message_text)
                logger.info(f"User {user_id}: отправлено {sent}, ошибок {errors}")
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка в spam_task: {e}")
            await asyncio.sleep(1)

@dp.message(Command("spam"))
async def cmd_spam(message: types.Message):
    """Начало бесконечной рассылки"""
    user_id = message.from_user.id
    
    if user_id not in user_bots or not user_bots[user_id]:
        await message.answer("❌ У вас нет добавленных ботов! Используйте /addbot")
        return
    
    await message.answer(
        "🌀 <b>Введите сообщение для бесконечной рассылки:</b>\n\n"
        "⚠️ Сообщения будут отправляться каждые 0.5 секунд!\n"
        "Для остановки: /stop",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    """Остановка рассылки"""
    user_id = message.from_user.id
    
    if user_id in active_spam_tasks:
        active_spam_tasks[user_id].cancel()
        del active_spam_tasks[user_id]
        await message.answer("🛑 Рассылка остановлена")
    else:
        await message.answer("ℹ️ Нет активных рассылок")

@dp.message()
async def process_any_message(message: types.Message):
    """Обработка обычных сообщений (для рассылки)"""
    user_id = message.from_user.id
    message_text = message.text
    
    # Игнорируем команды
    if message_text.startswith('/'):
        return
    
    # Проверяем, есть ли у пользователя боты
    if user_id not in user_bots or not user_bots[user_id]:
        return
    
    # Определяем режим по последней команде (упрощенная логика)
    # В реальном боте нужно использовать FSM
    
    # Если сообщение длинное, считаем его для рассылки
    if len(message_text) > 5:
        await message.answer("🚀 Начинаю рассылку...")
        
        total_sent = 0
        total_errors = 0
        
        for username, bot_data in user_bots[user_id].items():
            token = bot_data['token']
            sent, errors = await send_to_all_chats(token, message_text)
            total_sent += sent
            total_errors += errors
        
        await message.answer(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"📤 Отправлено: {total_sent}\n"
            f"❌ Ошибок: {total_errors}",
            parse_mode=ParseMode.HTML
        )

async def main():
    """Основная функция запуска бота"""
    # Введите ваш токен здесь
    BOT_TOKEN = "ВАШ_ТОКЕН_БОТА_МЕНЕДЖЕРА"
    
    if BOT_TOKEN == "8563807556:AAEjUX7i4gGCBV97SVNGeZV83fwsj7o8cZU":
        print("⚠️  ВНИМАНИЕ: Замените 'ВАШ_ТОКЕН_БОТА_МЕНЕДЖЕРА' на реальный токен!")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
