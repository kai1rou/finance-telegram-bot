from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

#главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить расход"), KeyboardButton(text="💰 Добавить доход")],
        [KeyboardButton(text="📊 Отчет"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)

#категории расходов
expense_categories_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍔 Еда"), KeyboardButton(text="🚗 Транспорт"), KeyboardButton(text="🏠 Дом")],
        [KeyboardButton(text="🎮 Развлечения"), KeyboardButton(text="👚 Одежда"), KeyboardButton(text="💊 Здоровье")],
        [KeyboardButton(text="✈️ Путешествия"), KeyboardButton(text="📚 Образование"), KeyboardButton(text="💼 Прочее")],
        [KeyboardButton(text="↩️ Назад")]
    ],
    resize_keyboard=True
)

#периоды для отчета
report_period_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="За день", callback_data="report_day"),
            InlineKeyboardButton(text="За неделю", callback_data="report_week")
        ],
        [
            InlineKeyboardButton(text="За месяц", callback_data="report_month"),
            InlineKeyboardButton(text="За все время", callback_data="report_all")
        ]
    ]
)
