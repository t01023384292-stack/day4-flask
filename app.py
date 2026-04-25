import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "board.db"

app = Flask(__name__)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            samples = [
                ("천천히 기록하는 아침", "오늘 아침은 커피 향과 함께 조용히 시작했다.", now),
                ("작은 습관의 힘", "하루 10분 글쓰기가 생각보다 큰 변화를 만든다.", now),
                ("따뜻한 미니멀리즘", "비워낸 공간 덕분에 오히려 집중이 선명해졌다.", now),
                ("한 줄 회고", "잘한 점 하나를 적는 습관이 하루를 정리해준다.", now),
            ]
            conn.executemany(
                "INSERT INTO posts (title, content, created_at) VALUES (?, ?, ?)",
                samples,
            )


@app.route("/")
def post_list():
    with get_db_connection() as conn:
        posts = conn.execute(
            "SELECT id, title, content, created_at FROM posts ORDER BY id DESC"
        ).fetchall()
    return render_template("list.html", posts=posts)


@app.route("/posts/<int:post_id>")
def post_detail(post_id: int):
    with get_db_connection() as conn:
        post = conn.execute(
            "SELECT id, title, content, created_at FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
    if post is None:
        abort(404)
    return render_template("detail.html", post=post)


@app.route("/posts/new", methods=["GET", "POST"])
def post_create():
    error = None
    title_value = ""
    content_value = ""

    if request.method == "POST":
        title_value = request.form.get("title", "").strip()
        content_value = request.form.get("content", "").strip()

        if not title_value or not content_value:
            error = "제목과 내용을 모두 입력해 주세요."
        else:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO posts (title, content, created_at) VALUES (?, ?, ?)",
                    (title_value, content_value, created_at),
                )
                new_id = cursor.lastrowid
            return redirect(url_for("post_detail", post_id=new_id))

    return render_template(
        "new.html",
        error=error,
        title_value=title_value,
        content_value=content_value,
    )


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
