import os
import sqlite3
from datetime import datetime
from pathlib import Path

import math

from flask import Flask, abort, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "board.db")))

app = Flask(__name__)


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
                created_at TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # 기존 테이블에 views 컬럼이 없으면 추가
        cols = [row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()]
        if "views" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
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


PER_PAGE = 10

SORT_OPTIONS = {
    "latest": "id DESC",
    "oldest": "id ASC",
    "views": "views DESC, id DESC",
}


@app.route("/")
@app.route("/page/<int:page>")
def post_list(page=1):
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "latest")
    if sort not in SORT_OPTIONS:
        sort = "latest"
    order_by = SORT_OPTIONS[sort]

    with get_db_connection() as conn:
        if q:
            like = f"%{q}%"
            total = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE title LIKE ? OR content LIKE ?",
                (like, like),
            ).fetchone()[0]
            total_pages = max(1, math.ceil(total / PER_PAGE))
            page = max(1, min(page, total_pages))
            offset = (page - 1) * PER_PAGE
            posts = conn.execute(
                f"SELECT id, title, content, created_at, views FROM posts WHERE title LIKE ? OR content LIKE ? ORDER BY {order_by} LIMIT ? OFFSET ?",
                (like, like, PER_PAGE, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            total_pages = max(1, math.ceil(total / PER_PAGE))
            page = max(1, min(page, total_pages))
            offset = (page - 1) * PER_PAGE
            posts = conn.execute(
                f"SELECT id, title, content, created_at, views FROM posts ORDER BY {order_by} LIMIT ? OFFSET ?",
                (PER_PAGE, offset),
            ).fetchall()

    return render_template(
        "list.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
        total=total,
        q=q,
        sort=sort,
    )


@app.route("/posts/<int:post_id>")
def post_detail(post_id: int):
    with get_db_connection() as conn:
        conn.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
        post = conn.execute(
            "SELECT id, title, content, created_at, views FROM posts WHERE id = ?",
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
        page_title="글쓰기",
        form_title="새 글 쓰기",
        submit_label="저장하기",
        form_action=url_for("post_create"),
        cancel_url=url_for("post_list"),
    )


@app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
def post_edit(post_id: int):
    with get_db_connection() as conn:
        post = conn.execute(
            "SELECT id, title, content, created_at FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()

    if post is None:
        abort(404)

    error = None
    title_value = post["title"]
    content_value = post["content"]

    if request.method == "POST":
        title_value = request.form.get("title", "").strip()
        content_value = request.form.get("content", "").strip()

        if not title_value or not content_value:
            error = "제목과 내용을 모두 입력해 주세요."
        else:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE posts SET title = ?, content = ? WHERE id = ?",
                    (title_value, content_value, post_id),
                )
            return redirect(url_for("post_detail", post_id=post_id))

    return render_template(
        "new.html",
        error=error,
        title_value=title_value,
        content_value=content_value,
        page_title="글수정",
        form_title="글 수정하기",
        submit_label="수정하기",
        form_action=url_for("post_edit", post_id=post_id),
        cancel_url=url_for("post_detail", post_id=post_id),
    )


@app.route("/posts/<int:post_id>/delete", methods=["POST"])
def post_delete(post_id: int):
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

    if cursor.rowcount == 0:
        abort(404)

    return redirect(url_for("post_list"))


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
