import mysql.connector
from mysql.connector import errorcode
from tkinter import messagebox
from contextlib import contextmanager

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "posdb"
}

TAX_RATE = 0.12

def connect_db():
    cfg = DB_CONFIG.copy()
    try:
        return mysql.connector.connect(**cfg)
    except mysql.connector.Error as err:
        if getattr(err, "errno", None) == errorcode.ER_BAD_DB_ERROR:
            try:
                cfg_no_db = cfg.copy()
                cfg_no_db.pop("database", None)
                tmp = mysql.connector.connect(**cfg_no_db)
                cur = tmp.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} DEFAULT CHARACTER SET 'utf8mb4'")
                tmp.commit()
                cur.close()
                tmp.close()
                return mysql.connector.connect(**cfg)
            except mysql.connector.Error as e2:
                messagebox.showerror("Database Error", f"Failed to create database '{DB_CONFIG['database']}':\n{e2}")
                return None
        else:
            messagebox.showerror("Database Connection Error",
                                 f"Could not connect to MySQL server.\n\nError: {err}\n\nCheck DB credentials.")
            return None

@contextmanager
def db_cursor():
    db = connect_db()
    if not db:
        yield None
    else:
        cur = db.cursor()
        try:
            yield cur
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
            db.close()

def init_db_tables():
    with db_cursor() as cur:
        if not cur:
            return False
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password VARCHAR(255)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) UNIQUE,
            price DECIMAL(10,2) NOT NULL,
            quantity INT NOT NULL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) UNIQUE,
            price DECIMAL(10,2) NOT NULL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item VARCHAR(200),
            price DECIMAL(10,2),
            qty INT,
            total DECIMAL(10,2),
            date DATETIME,
            cashier VARCHAR(100)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date_time DATETIME,
            total_amount DECIMAL(10,2),
            payment_amount DECIMAL(10,2),
            change_amount DECIMAL(10,2)
        )
        """)
    return True
