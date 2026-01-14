import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище ботов пользователя
user_bots = {}  # {user_id: {bot_username: token}}

async def send_to_all_chats(bot_token: str, message_text: str):
    """Отправляет сообщение во все чаты, где состоит бот"""
    try:
        bot = Bot(token=bot_token)
        
        # Получаем обновления бота (чаты где он состоит)
        updates = await bot.get_updates(limit=100, offset=-100)
        
        sent_count = 0
        error_count = 0
        chat_ids = set()
        
        # Собираем уникальные chat_id из обновлений
        for update in updates:
            if update.message:
                chat_ids.add(update.message.chat.id)
            if update.callback_query:
                chat_ids.add(update.callback_query.message.chat.id)
        
        # Отправляем сообщение в каждый чат
        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
                await asyncio.sleep(0.5)  # Задержка между отправками
            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка отправки в chat_id {chat_id}: {e}")
        
        await bot.session.close()
        return sent_count, error_count
        
    except Exception as e:
        logger.error(f"Ошибка в send_to_all_chats: {e}")
        return 0, 1

async def main():
    bot = Bot(token="8563807556:AAEjUX7i4gGCBV97SVNGeZV83fwsj7o8cZU")
    dp = Dispatcher()
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "🤖 *Бот для массовой рассылки*\n\n"
            "Команды:\n"
            "/addbot - добавить бота\n"
            "/send - отправить сообщение всем\n"
            "/spam - бесконечная рассылка\n"
            "/stop - остановить рассылку",
            parse_mode=ParseMode.MARKDOWN
        )
    
    @dp.message(Command("addbot"))
    async def cmd_addbot(message: types.Message):
        await message.answer("Пришлите токен бота (формат: 123456:ABCdef)")
    
    @dp.message(lambda message: ':' in message.text and message.text.split(':')[0].isdigit())
    async def process_token(message: types.Message):
        token = message.text.strip()
        try:
            test_bot = Bot(token=token)
            bot_info = await test_bot.get_me()
            await test_bot.session.close()
            
            user_id = message.from_user.id
            if user_id not in user_bots:
                user_bots[user_id] = {}
            
            user_bots[user_id][bot_info.username] = token
            
            await message.answer(
                f"✅ Бот @{bot_info.username} добавлен!\n"
                f"ID: {bot_info.id}\n"
                f"Имя: {bot_info.first_name}"
            )
        except:
            await message.answer("❌ Неверный токен!")
    
    @dp.message(Command("send"))
    async def cmd_send(message: types.Message):
        user_id = message.from_user.id
        if user_id not in user_bots or not user_bots[user_id]:
            await message.answer("❌ У вас нет добавленных ботов!")
            return
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        for username in user_bots[user_id].keys():
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(f"@{username}", callback_data=f"send:{username}")
            ])
        
        await message.answer("Выберите бота:", reply_markup=keyboard)
    
    @dp.callback_query(lambda c: c.data.startswith("send:"))
    async def process_send_bot(callback: types.CallbackQuery):
        username = callback.data.split(":")[1]
        await callback.message.answer(
            f"Выбран бот @{username}\n"
            f"Теперь отправьте сообщение для рассылки"
        )
        # Сохраняем выбранного бота (можно использовать FSM, здесь упрощенно)
        await callback.answer()
    
    # Глобальная переменная для хранения активных задач рассылки
    active_tasks = {}
    
    @dp.message(Command("spam"))
    async def cmd_spam(message: types.Message):
        user_id = message.from_user.id
        if user_id not in user_bots or not user_bots[user_id]:
            await message.answer("❌ У вас нет добавленных ботов!")
            return
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        for username in user_bots[user_id].keys():
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(f"@{username}", callback_data=f"spam:{username}")
            ])
        
        await message.answer(
            "Выберите бота для бесконечной рассылки:\n"
            "⚠️ Сообщения будут отправляться каждые 0.5 сек!",
            reply_markup=keyboard
        )
    
    async def spam_task(user_id: int, bot_username: str, message_text: str):
        """Задача бесконечной рассылки"""
        token = user_bots[user_id][bot_username]
        while True:
            sent, errors = await send_to_all_chats(token, message_text)
            await asyncio.sleep(0.5)  # Задержка 0.5 секунды
    
    @dp.message()
    async def process_message(message: types.Message):
        # Если сообщение пришло после выбора бота (упрощенная логика)
        user_id = message.from_user.id
        if user_id in user_bots and len(message.text) > 10:
            # Ищем последнего выбранного бота (в реальном боте нужно использовать FSM)
            for bot_username in user_bots[user_id].keys():
                if bot_username in message.text.lower():
                    continue
            
            # Простая рассылка
            if user_bots[user_id]:
                bot_username = list(user_bots[user_id].keys())[0]
                await message.answer(f"Начинаю рассылку через @{bot_username}...")
                sent, errors = await send_to_all_chats(user_bots[user_id][bot_username], message.text)
                await message.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {errors}")
    
    @dp.message(Command("stop"))
    async def cmd_stop(message: types.Message):
        user_id = message.from_user.id
        if user_id in active_tasks:
            active_tasks[user_id].cancel()
            del active_tasks[user_id]
            await message.answer("🛑 Рассылка остановлена")
        else:
            await message.answer("❌ Нет активных рассылок")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
