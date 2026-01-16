import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove

#ПОЛУЧЕНИЕ ТОКЕНА
BOT_TOKEN = os.environ.get("BOT_TOKEN")


if not BOT_TOKEN:
    try:
        from config import BOT_TOKEN as config_token
        BOT_TOKEN = config_token
    except ImportError:
        raise ValueError("❌ BOT_TOKEN не найден! Добавьте его в переменные окружения на Render.")

#ИМПОРТЫ ИЗ ПРОЕКТА
from database import Database
from keyboards import *

#настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#инициализация бота и БД
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database("expenses.db")


#состояния для добавления транзакции
class TransactionStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_comment = State()


#ОБРАБОТЧИКИ КОМАНД

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer(
        "👋 **Привет! Я бот для учета финансов.**\n\n"
        "Я помогу вам контролировать расходы и доходы:\n"
        "• Добавлять операции\n"
        "• Смотреть отчеты\n"
        "• Анализировать статистику\n\n"
        "Используйте кнопки ниже или команды:",
        reply_markup=main_kb,
        parse_mode='Markdown'
    )



@dp.message(Command("help"))
async def send_help(message: types.Message):
    await message.answer(
        "📋 **Доступные команды:**\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/add_expense - добавить расход\n"
        "/add_income - добавить доход\n"
        "/report - отчет\n"
        "/stats - статистика\n\n"
        "Или используйте кнопки на клавиатуре ↓",
        parse_mode='Markdown'
    )


#ОБРАБОТЧИКИ КНОПОК

#кнопка  Добавить расход
@dp.message(F.text == "➕ Добавить расход")
async def add_expense_start(message: types.Message, state: FSMContext):
    await message.answer("Выберите категорию расхода:", reply_markup=expense_categories_kb)
    await state.set_state(TransactionStates.waiting_for_category)
    await state.update_data(trans_type="expense")


#кнопка  Добавить доход
@dp.message(F.text == "💰 Добавить доход")
async def add_income_start(message: types.Message, state: FSMContext):
    await message.answer("Введите категорию дохода (например: Зарплата, Фриланс):",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(TransactionStates.waiting_for_category)
    await state.update_data(trans_type="income")


#назад в главное меню
@dp.message(F.text == "↩️ Назад")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_kb)


#FSM: ДОБАВЛЕНИЕ ТРАНЗАКЦИИ

#шаг 1: Получение категории
@dp.message(TransactionStates.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Введите сумму (только число, например: 1500.50):")
    await state.set_state(TransactionStates.waiting_for_amount)


#шаг 2: Получение суммы
@dp.message(TransactionStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (положительное число):")
        return

    await state.update_data(amount=amount)
    await message.answer("Добавьте комментарий (или напишите 'нет' для пропуска):")
    await state.set_state(TransactionStates.waiting_for_comment)


#шаг 3: Получение комментария и сохранение
@dp.message(TransactionStates.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = None if message.text.lower() in ['нет', 'no', 'пропустить', 'skip'] else message.text

    data = await state.get_data()

    #сохраняем в базу данных
    db.add_transaction(
        user_id=message.from_user.id,
        trans_type=data['trans_type'],
        category=data['category'],
        amount=data['amount'],
        comment=comment
    )

    #формируем сообщение
    trans_type_rus = "расход" if data['trans_type'] == 'expense' else "доход"
    response = (
        f"✅ **{trans_type_rus.capitalize()} добавлен!**\n"
        f"• Категория: {data['category']}\n"
        f"• Сумма: {data['amount']:.2f} руб.\n"
        f"• Комментарий: {comment if comment else '—'}"
    )

    await message.answer(response, reply_markup=main_kb, parse_mode='Markdown')
    await state.clear()


#ОТЧЕТЫ

#кнопка  Отчет
@dp.message(F.text == "📊 Отчет")
async def show_report_menu(message: types.Message):
    await message.answer("Выберите период для отчета:", reply_markup=report_period_kb)


#обработка inline-кнопок отчетов
@dp.callback_query(F.data.startswith('report_'))
async def process_report_callback(callback_query: types.CallbackQuery):
    period_map = {
        'report_day': 'day',
        'report_week': 'week',
        'report_month': 'month',
        'report_all': 'all'
    }
    period = period_map[callback_query.data]

    transactions = db.get_transactions(callback_query.from_user.id, period)

    if not transactions:
        await callback_query.message.edit_text(f"📭 За {period} операций нет.")
        return

    #формируем отчет\
    report_lines = [f"📋 **Отчет за {period}:**\n"]
    total_expense = 0
    total_income = 0

    for trans in transactions[:15]:  #показываем только последние 15 операций
        trans_type, category, amount, date, comment = trans

        #ворматируем дату
        if isinstance(date, str):
            date_str = date[:10]
        else:
            date_str = date.strftime("%d.%m.%Y") if hasattr(date, 'strftime') else str(date)[:10]

        icon = "➖" if trans_type == 'expense' else "➕"
        if trans_type == 'expense':
            total_expense += amount
        else:
            total_income += amount

        comment_text = f" ({comment})" if comment else ""
        report_lines.append(f"{icon} {date_str} | {category}: {amount:.2f} руб.{comment_text}")

    if len(transactions) > 15:
        report_lines.append(f"\n... и еще {len(transactions) - 15} операций")

    report_lines.append(f"\n📊 **Итого:**")
    report_lines.append(f"Расходы: {total_expense:.2f} руб.")
    report_lines.append(f"Доходы: {total_income:.2f} руб.")
    report_lines.append(f"Баланс: {total_income - total_expense:.2f} руб.")

    await callback_query.message.edit_text("\n".join(report_lines), parse_mode='Markdown')
    await callback_query.answer()


#К\кнопка  Статистика
@dp.message(F.text == "📈 Статистика")
async def show_statistics(message: types.Message):
    #простая статистика
    transactions = db.get_transactions(message.from_user.id, 'month')

    if not transactions:
        await message.answer("📭 За этот месяц операций нет.")
        return

    total_expense = 0
    total_income = 0
    categories = {}

    for trans in transactions:
        trans_type, category, amount, date, comment = trans
        if trans_type == 'expense':
            total_expense += amount
            categories[category] = categories.get(category, 0) + amount
        else:
            total_income += amount

    response = ["📈 **Статистика за месяц:**\n"]
    response.append(f"• Всего операций: {len(transactions)}")
    response.append(f"• Расходы: {total_expense:.2f} руб.")
    response.append(f"• Доходы: {total_income:.2f} руб.")
    response.append(f"• Баланс: {total_income - total_expense:.2f} руб.")

    if categories:
        response.append("\n📊 **Расходы по категориям:**")
        for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0
            response.append(f"  {category}: {amount:.2f} руб. ({percentage:.1f}%)")

    await message.answer("\n".join(response), parse_mode='Markdown')


#кнопка  Помощь
@dp.message(F.text == "ℹ️ Помощь")
async def show_help(message: types.Message):
    await send_help(message)


#ЗАПУСК БОТА

async def main():
    print("=" * 50)
    print("🤖 FINANCE BOT запущен! (aiogram 3.x)")
    print(f"🔑 Токен получен: {'✅ Да' if BOT_TOKEN else '❌ Нет'}")
    if BOT_TOKEN:
        print(f"📝 Токен (первые 10 символов): {BOT_TOKEN[:10]}...")
    print("📊 База данных: expenses.db")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("⏳ Ожидание сообщений...")
    print("=" * 50)

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
        db.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        db.close()


if __name__ == '__main__':
    asyncio.run(main())
