#!/bin/bash
# Скрипт запуска Antic Browser для macOS/Linux

cd "$(dirname "$0")"

# Проверяем наличие виртуального окружения
if [ ! -d ".venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создаем виртуальное окружение..."
    python3 -m venv .venv
    
    echo "Активируем окружение и устанавливаем зависимости..."
    source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
else
    source .venv/bin/activate
fi

# Запускаем программу
echo "🚀 Запускаем Antic Browser..."
python antic.py
