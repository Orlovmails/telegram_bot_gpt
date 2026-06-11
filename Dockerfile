FROM python:3.10

# Встановлюємо робочу директорію
WORKDIR /app

# Спочатку оновлюємо сам інструмент pip всередині контейнера
RUN pip install --upgrade pip

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо наші 4 чисті бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь інший код проекту
COPY . .

# Команда для запуска
CMD ["python", "bot.py"]