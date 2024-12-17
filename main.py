import requests
import sqlite3
import flet as ft
import os

db_path = 'jma2.db'

if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL,
            number INTEGER NOT NULL,
            "Presenting organization" TEXT NOT NULL,
            "Announcement date and time" TEXT NOT NULL,
            "weather forecast" TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()



