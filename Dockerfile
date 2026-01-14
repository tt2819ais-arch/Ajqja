FROM python:3.11-slim

WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY bot_manager.py .

# Запуск бота
CMD ["python", "bot_manager.py"]
