import psycopg2
import psycopg2.extras
import time
from ..core.config import settings


def get_postgres_connection():
    retries = 10
    delay_seconds = 2
    last_exc = None
    for _ in range(retries):
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                dbname=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
            )
            return conn
        except Exception as exc:
            last_exc = exc
            time.sleep(delay_seconds)
    raise last_exc


def init_schema():
    conn = get_postgres_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            twofa_secret TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS faqs (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            customer_name VARCHAR(255),
            subject TEXT NOT NULL,
            category VARCHAR(100),
            description TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'open',
            priority VARCHAR(50) DEFAULT 'medium',
            session_id VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    # Perform ALTERs to add columns if the table already existed
    try:
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255)")
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS category VARCHAR(100)")
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium'")
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS session_id VARCHAR(64)")
    except Exception:
        pass
    cur.close()
    conn.close()


