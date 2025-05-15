# database.py

import sqlite3

class DatabaseManager:
    def __init__(self, db_path='finance.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def execute(self, *args, **kwargs):
        self.ensure_connected()
        return self.cursor.execute(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        self.ensure_connected()
        return self.cursor.executescript(*args, **kwargs)

    def fetchone(self):
        self.ensure_connected()
        return self.cursor.fetchone()

    def fetchall(self):
        self.ensure_connected()
        return self.cursor.fetchall()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def ensure_connected(self):
        if self.conn is None or self.cursor is None:
            self.connect()
