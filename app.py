from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB = "rasmm.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            category TEXT,
            service TEXT,
            link TEXT,
            quantity INTEGER,
            price REAL,
            status TEXT DEFAULT 'Bekliyor',
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            amount REAL,
            txid TEXT,
            network TEXT DEFAULT 'BEP-20',
            status TEXT DEFAULT 'Bekliyor',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "project": "RA SMM",
        "message": "RA SMM API çalışıyor."
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/user", methods=["POST"])
def create_user():
    data = request.get_json() or {}

    telegram_id = str(data.get("telegram_id", "")).strip()
    username = data.get("username", "")
    first_name = data.get("first_name", "")

    if not telegram_id:
        return jsonify({"error": "telegram_id gerekli"}), 400

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    if user:
        conn.execute("""
            UPDATE users
            SET username = ?, first_name = ?
            WHERE telegram_id = ?
        """, (username, first_name, telegram_id))
    else:
        conn.execute("""
            INSERT INTO users
            (telegram_id, username, first_name, balance, created_at)
            VALUES (?, ?, ?, 0, ?)
        """, (
            telegram_id,
            username,
            first_name,
            datetime.utcnow().isoformat()
        ))

    conn.commit()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    conn.close()

    return jsonify(dict(user))


@app.route("/api/user/<telegram_id>")
def get_user(telegram_id):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    return jsonify(dict(user))


@app.route("/api/balance/<telegram_id>")
def get_balance(telegram_id):
    conn = get_db()

    user = conn.execute(
        "SELECT balance FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({"balance": 0})

    return jsonify({
        "balance": float(user["balance"])
    })


@app.route("/api/order", methods=["POST"])
def create_order():
    data = request.get_json() or {}

    telegram_id = str(data.get("telegram_id", "")).strip()
    category = data.get("category", "")
    service = data.get("service", "")
    link = data.get("link", "")
    quantity = int(data.get("quantity", 0))
    price = float(data.get("price", 0))

    if not telegram_id:
        return jsonify({"error": "telegram_id gerekli"}), 400

    if not service or not link:
        return jsonify({"error": "Hizmet ve link gerekli"}), 400

    if quantity <= 0:
        return jsonify({"error": "Geçersiz miktar"}), 400

    if price <= 0:
        return jsonify({"error": "Geçersiz fiyat"}), 400

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    balance = float(user["balance"])

    if balance < price:
        conn.close()
        return jsonify({
            "error": "Yetersiz bakiye",
            "balance": balance,
            "required": price
        }), 400

    new_balance = balance - price

    conn.execute("""
        UPDATE users
        SET balance = ?
        WHERE telegram_id = ?
    """, (new_balance, telegram_id))

    cursor = conn.execute("""
        INSERT INTO orders
        (telegram_id, category, service, link, quantity, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Bekliyor', ?)
    """, (
        telegram_id,
        category,
        service,
        link,
        quantity,
        price,
        datetime.utcnow().isoformat()
    ))

    order_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "order_id": order_id,
        "new_balance": new_balance,
        "status": "Bekliyor"
    })


@app.route("/api/orders/<telegram_id>")
def get_orders(telegram_id):
    conn = get_db()

    orders = conn.execute("""
        SELECT *
        FROM orders
        WHERE telegram_id = ?
        ORDER BY id DESC
    """, (telegram_id,)).fetchall()

    conn.close()

    return jsonify([dict(order) for order in orders])


@app.route("/api/payment", methods=["POST"])
def create_payment():
    data = request.get_json() or {}

    telegram_id = str(data.get("telegram_id", "")).strip()
    amount = float(data.get("amount", 0))
    txid = data.get("txid", "")

    if not telegram_id or amount <= 0 or not txid:
        return jsonify({"error": "Eksik ödeme bilgisi"}), 400

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    cursor = conn.execute("""
        INSERT INTO payments
        (telegram_id, amount, txid, network, status, created_at)
        VALUES (?, ?, ?, 'BEP-20', 'Bekliyor', ?)
    """, (
        telegram_id,
        amount,
        txid,
        datetime.utcnow().isoformat()
    ))

    payment_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "payment_id": payment_id,
        "status": "Bekliyor"
    })


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
