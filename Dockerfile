FROM python:3.10-slim

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо бібліотеки без кешування, щоб зекономити місце
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь проект (коди, картинки, промпти) у контейнер
COPY . .

# Команда для запуску бота
CMD ["python", "bot.py"]