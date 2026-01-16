import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_file="expenses.db"):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_table()
        print(f"✅ База данных подключена: {db_file}")

    def create_table(self):
        """Создает таблицу для финансовых операций"""
        with self.connection:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    comment TEXT
                )
            ''')
            #создаем индекс для быстрого поиска по пользователю и дате
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_date 
                ON transactions (user_id, date)
            ''')
        print("✅ Таблица 'transactions' создана/проверена")

    def add_transaction(self, user_id: int, trans_type: str, category: str, amount: float, comment: str = None):
        """Добавляет новую транзакцию"""
        with self.connection:
            self.cursor.execute('''
                INSERT INTO transactions (user_id, type, category, amount, comment, date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, trans_type, category, amount, comment, datetime.now()))
        return self.cursor.lastrowid

    def get_transactions(self, user_id: int, period: str = 'month'):
        """Получает транзакции за период"""
        now = datetime.now()

        if period == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'all':
            start_date = datetime(2000, 1, 1)  # Очень старая дата
        else:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        with self.connection:
            self.cursor.execute('''
                SELECT type, category, amount, date, comment
                FROM transactions
                WHERE user_id = ? AND datetime(date) >= datetime(?)
                ORDER BY date DESC
            ''', (user_id, start_date))
            return self.cursor.fetchall()

    def close(self):
        """Закрывает соединение с БД"""
        self.connection.close()
        print("📊 Соединение с БД закрыто")
