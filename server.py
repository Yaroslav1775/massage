from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import hashlib

app = FastAPI()

# Разрешаем запросы с любого источника (для тестов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- МОДЕЛИ ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class MessageCreate(BaseModel):
    sender: str
    receiver: str
    text: str

class Message(BaseModel):
    id: int
    sender: str
    receiver: str
    text: str
    timestamp: str

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def get_db():
    conn = sqlite3.connect("messenger.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# --- ХЕЛПЕРЫ ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- ЭНДПОИНТЫ ---
@app.post("/register")
def register(user: UserCreate):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (user.username, hash_password(user.password)))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()
    return {"message": "User registered"}

@app.post("/login")
def login(user: UserLogin):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (user.username,))
    row = c.fetchone()
    conn.close()
    if not row or row["password_hash"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}

@app.get("/users", response_model=List[str])
def get_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [row["username"] for row in c.fetchall()]
    conn.close()
    return users

@app.post("/send")
def send_message(msg: MessageCreate):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, receiver, text) VALUES (?, ?, ?)",
              (msg.sender, msg.receiver, msg.text))
    conn.commit()
    conn.close()
    return {"message": "Message sent"}

@app.get("/messages", response_model=List[Message])
def get_messages(user1: str, user2: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT * FROM messages WHERE
        (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY timestamp ASC''', (user1, user2, user2, user1))
    messages = [Message(**dict(row)) for row in c.fetchall()]
    conn.close()
    return messages 