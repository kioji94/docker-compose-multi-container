import os
import time

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),  # service name = DNS name on the compose network
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "appdb"),
    "user": os.getenv("POSTGRES_USER", "appuser"),
    "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
}


def get_conn(retries=10, delay=2):
    """Connect to PostgreSQL, retrying while the DB container finishes starting."""
    last_err = None
    for _ in range(retries):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.OperationalError as err:
            last_err = err
            time.sleep(delay)
    raise last_err


def init_db():
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    conn.close()


@app.route("/")
def index():
    return jsonify(
        service="web",
        message="Multi-container app: Flask + PostgreSQL via Docker Compose",
        endpoints=["/health", "/notes (GET, POST)"],
    )


@app.route("/health")
def health():
    try:
        conn = get_conn(retries=1, delay=0)
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return jsonify(status="ok", database="reachable")
    except Exception as err:  # noqa: BLE001
        return jsonify(status="degraded", database="unreachable", error=str(err)), 503


@app.route("/notes", methods=["GET"])
def list_notes():
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id, content, created_at FROM notes ORDER BY id")
        rows = cur.fetchall()
    conn.close()
    return jsonify(
        [{"id": r[0], "content": r[1], "created_at": r[2].isoformat()} for r in rows]
    )


@app.route("/notes", methods=["POST"])
def add_note():
    payload = request.get_json(silent=True) or {}
    content = (payload.get("content") or "").strip()
    if not content:
        return jsonify(error="'content' is required"), 400
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO notes (content) VALUES (%s) RETURNING id", (content,)
        )
        note_id = cur.fetchone()[0]
    conn.close()
    return jsonify(id=note_id, content=content), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
