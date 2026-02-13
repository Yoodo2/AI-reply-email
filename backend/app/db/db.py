import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "app.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mail_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            imap_host TEXT,
            imap_port INTEGER,
            smtp_host TEXT,
            smtp_port INTEGER,
            username TEXT,
            password TEXT,
            use_ssl INTEGER DEFAULT 1,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            keywords TEXT,
            is_default INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            variables TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            body_text TEXT,
            body_html TEXT,
            received_at TEXT,
            language TEXT,
            translation TEXT,
            status TEXT DEFAULT 'pending',
            category_id INTEGER,
            confidence REAL,
            ai_reply TEXT,
            final_reply TEXT,
            created_at TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER,
            ai_category_id INTEGER,
            ai_confidence REAL,
            final_category_id INTEGER,
            sent_at TEXT,
            smtp_response TEXT,
            FOREIGN KEY(email_id) REFERENCES emails(id)
        )
        """
    )

    conn.commit()
    seed_defaults(conn)
    conn.close()


def seed_defaults(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(1) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO categories (name, description, keywords, is_default, priority) VALUES (?, ?, ?, ?, ?)"
            , ("默认", "未匹配到其他分类时使用", "", 1, 0)
        )
        cursor.execute(
            "INSERT INTO templates (category_id, name, content, variables) VALUES (?, ?, ?, ?)"
            , (1, "默认回复", "您好，已收到您的来信，我们会尽快处理并回复您。", "")
        )
        conn.commit()


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cur = conn.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return list(rows)


def execute(query: str, params: Iterable[Any] = ()) -> int:
    conn = get_connection()
    cur = conn.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def execute_many(query: str, params_list: Iterable[Iterable[Any]]) -> None:
    conn = get_connection()
    conn.executemany(query, params_list)
    conn.commit()
    conn.close()


def set_setting(key: str, value: str) -> None:
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    row = fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def get_settings() -> Dict[str, str]:
    rows = fetch_all("SELECT key, value FROM settings")
    return {row["key"]: row["value"] for row in rows}
