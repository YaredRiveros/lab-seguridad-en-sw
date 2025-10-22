import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), 'data.db')

def init_db():
    if os.path.exists(DB):
        print('Removing existing DB...')
        os.remove(DB)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, bio TEXT)''')
    users = [
        ('alice', 'Developer'),
        ('bob', 'Tester'),
        ('admin', "The admin user. Secret: s3cr3t_admin_password")
    ]
    c.executemany('INSERT INTO users (username, bio) VALUES (?, ?)', users)
    conn.commit()
    conn.close()
    print('Initialized', DB)

if __name__ == '__main__':
    init_db()
