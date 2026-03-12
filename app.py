import sqlite3
import re
import shutil
from pathlib import Path
from html import escape

from flask import Flask, abort, g, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

try:
    import markdown as markdown_lib
except Exception:
    markdown_lib = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "vault.db"
UPLOADS_DIR = BASE_DIR / "uploads"

app = Flask(__name__)

UPLOADS_DIR.mkdir(exist_ok=True)


@app.template_filter("nl2br")
def nl2br(value):
    paragraphs = [line.strip() for line in value.splitlines() if line.strip()]
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def _render_markdown_fallback(text):
    html_blocks = []
    in_code_block = False
    code_lines = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_blocks.append("</ul>")
            in_list = False

    def format_inline(value):
        value = escape(value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
        value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', value)
        return value

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            close_list()
            if in_code_block:
                html_blocks.append("<pre><code>" + escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not stripped:
            close_list()
            continue

        if stripped.startswith("# "):
            close_list()
            html_blocks.append(f"<h1>{format_inline(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            close_list()
            html_blocks.append(f"<h2>{format_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            close_list()
            html_blocks.append(f"<h3>{format_inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_blocks.append("<ul>")
                in_list = True
            html_blocks.append(f"<li>{format_inline(stripped[2:])}</li>")
            continue

        close_list()
        html_blocks.append(f"<p>{format_inline(stripped)}</p>")

    close_list()

    if in_code_block:
        html_blocks.append("<pre><code>" + escape("\n".join(code_lines)) + "</code></pre>")

    return "".join(html_blocks)


@app.template_filter("render_markdown")
def render_markdown(value):
    if markdown_lib is not None:
        return markdown_lib.markdown(
            value,
            extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
        )
    return _render_markdown_fallback(value)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with open(BASE_DIR / "schema.sql", "r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())
    db.commit()


def seed_db():
    db = get_db()
    existing = db.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"]
    if existing:
        return

    db.execute(
        """
        INSERT INTO courses (title, description, cover_url)
        VALUES (?, ?, ?)
        """,
        (
            "Formacao Pentest Profissional",
            "A structured study vault for cybersecurity modules, lesson notes, and supporting files.",
            "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
        ),
    )
    course_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    modules = [
        ("Introduction to Information Security", "Core concepts, risks, terminology, and legislation.", 1),
        ("Linux Terminal Mastery", "Commands, users, networking, editors, and shell productivity.", 2),
        ("TCP/IP for Pentesters", "Protocols, packet flow, and network analysis fundamentals.", 3),
    ]

    module_ids = []
    for title, summary, position in modules:
        db.execute(
            """
            INSERT INTO modules (course_id, title, summary, position)
            VALUES (?, ?, ?, ?)
            """,
            (course_id, title, summary, position),
        )
        module_ids.append(db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])

    lessons = [
        (
            module_ids[0],
            "Security Terminology",
            "Threats, vulnerabilities, and risks need to be separated clearly. A vulnerability is a weakness, a threat is a potential cause of harm, and risk is the impact plus likelihood.",
            "Glossary PDF",
            "https://example.com/security-terminology.pdf",
            1,
        ),
        (
            module_ids[1],
            "Introduction to the Terminal",
            "The terminal becomes more useful when commands are treated like building blocks. Search, filter, redirect, and inspect outputs before memorizing shortcuts.",
            None,
            None,
            1,
        ),
        (
            module_ids[1],
            "Introduction to Vim",
            "Vim is powerful once modes make sense. Normal mode is for movement and commands, insert mode is for text, and command mode is for save and quit actions.",
            "Editor VIM Part 1",
            "https://example.com/vim-intro.pdf",
            2,
        ),
        (
            module_ids[2],
            "Understanding DNS",
            "DNS translates names into IP addresses, but it also exposes valuable enumeration opportunities during recon and infrastructure mapping.",
            None,
            None,
            1,
        ),
    ]

    db.executemany(
        """
        INSERT INTO lessons (module_id, title, notes, attachment_label, attachment_url, position)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        lessons,
    )
    db.commit()


def query_one_or_404(query, params=()):
    row = get_db().execute(query, params).fetchone()
    if row is None:
        abort(404)
    return row


def next_position(table_name, foreign_key, parent_id):
    row = get_db().execute(
        f"SELECT COALESCE(MAX(position), 0) + 1 AS next_position FROM {table_name} WHERE {foreign_key} = ?",
        (parent_id,),
    ).fetchone()
    return row["next_position"]


def swap_positions(table_name, current_id, neighbor_id):
    db = get_db()
    current = db.execute(f"SELECT position FROM {table_name} WHERE id = ?", (current_id,)).fetchone()
    neighbor = db.execute(f"SELECT position FROM {table_name} WHERE id = ?", (neighbor_id,)).fetchone()
    if current is None or neighbor is None:
        return None

    db.execute(f"UPDATE {table_name} SET position = ? WHERE id = ?", (neighbor["position"], current_id))
    db.execute(f"UPDATE {table_name} SET position = ? WHERE id = ?", (current["position"], neighbor_id))
    db.commit()
    return {
        "current_id": current_id,
        "current_position": neighbor["position"],
        "neighbor_id": neighbor_id,
        "neighbor_position": current["position"],
    }


def lesson_excerpt(text, limit=150):
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def lesson_upload_dir(lesson_id):
    upload_dir = UPLOADS_DIR / str(lesson_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def remove_local_attachment(attachment_url):
    if not attachment_url or not attachment_url.startswith("/uploads/"):
        return

    parts = attachment_url.removeprefix("/uploads/").split("/", 1)
    if len(parts) != 2:
        return

    lesson_id, file_name = parts
    attachment_path = UPLOADS_DIR / lesson_id / file_name
    if attachment_path.exists():
        attachment_path.unlink()


def save_attachment_file(uploaded_file, lesson_id):
    if not uploaded_file or not uploaded_file.filename:
        return None, None

    safe_name = secure_filename(Path(uploaded_file.filename).name)
    if not safe_name:
        return None, None

    target_dir = lesson_upload_dir(lesson_id)
    target_path = target_dir / safe_name
    uploaded_file.save(target_path)
    return safe_name, f"/uploads/{lesson_id}/{safe_name}"


def import_course_from_directory(source_path):
    source = Path(source_path).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise ValueError("Directory not found.")

    db = get_db()
    title = source.name
    description = f"Imported from local folder: {source}"
    db.execute(
        "INSERT INTO courses (title, description, cover_url) VALUES (?, ?, ?)",
        (title, description, None),
    )
    course_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    module_dirs = sorted([item for item in source.iterdir() if item.is_dir() and not item.name.startswith(".")], key=lambda item: natural_key(item.name))

    for module_position, module_dir in enumerate(module_dirs, start=1):
        module_title = module_dir.name
        db.execute(
            """
            INSERT INTO modules (course_id, title, summary, position)
            VALUES (?, ?, ?, ?)
            """,
            (course_id, module_title, f"Imported from {module_title}.", module_position),
        )
        module_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

        lesson_dirs = sorted([item for item in module_dir.iterdir() if item.is_dir() and not item.name.startswith(".")], key=lambda item: natural_key(item.name))

        for lesson_position, lesson_dir in enumerate(lesson_dirs, start=1):
            notes_file = lesson_dir / "anotacoes.md"
            notes = ""
            if notes_file.exists():
                notes = notes_file.read_text(encoding="utf-8", errors="ignore")

            db.execute(
                """
                INSERT INTO lessons (module_id, title, notes, attachment_label, attachment_url, position)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    module_id,
                    lesson_dir.name,
                    notes or f"# {lesson_dir.name}\n\nImported lesson with no markdown notes yet.",
                    None,
                    None,
                    lesson_position,
                ),
            )
            lesson_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

            attachment_files = sorted(
                [
                    file_path
                    for file_path in lesson_dir.iterdir()
                    if file_path.is_file() and file_path.name.lower() != "anotacoes.md"
                ],
                key=lambda item: natural_key(item.name),
            )
            if attachment_files:
                attachment_file = attachment_files[0]
                safe_name = secure_filename(attachment_file.name)
                if safe_name:
                    target_dir = lesson_upload_dir(lesson_id)
                    target_path = target_dir / safe_name
                    shutil.copy2(attachment_file, target_path)
                    db.execute(
                        """
                        UPDATE lessons
                        SET attachment_label = ?, attachment_url = ?
                        WHERE id = ?
                        """,
                        (attachment_file.name, f"/uploads/{lesson_id}/{safe_name}", lesson_id),
                    )

    db.commit()
    return course_id


def import_course_from_upload(files):
    uploaded_files = [file for file in files if file and file.filename]
    if not uploaded_files:
        raise ValueError("No files uploaded.")

    normalized_files = []
    top_level_names = set()
    for file in uploaded_files:
        parts = [part for part in Path(file.filename).parts if part not in ("", ".")]
        if len(parts) < 2 or any(part.startswith(".") for part in parts):
            continue
        top_level_names.add(parts[0])
        normalized_files.append((parts, file))

    if not normalized_files or len(top_level_names) != 1:
        raise ValueError("Invalid uploaded folder structure.")

    course_title = next(iter(top_level_names))
    db = get_db()
    db.execute(
        "INSERT INTO courses (title, description, cover_url) VALUES (?, ?, ?)",
        (course_title, f"Imported from uploaded folder: {course_title}", None),
    )
    course_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    modules_map = {}
    module_records = []
    lesson_records = {}

    for parts, file in normalized_files:
        if len(parts) < 4:
            continue

        _, module_title, lesson_title, file_name = parts[0], parts[1], parts[2], parts[-1]
        modules_map.setdefault(module_title, {})
        lesson_records.setdefault(module_title, {})
        lesson_records[module_title].setdefault(lesson_title, {"notes": "", "attachment_file": None, "attachment_name": None})

        if file_name.lower() == "anotacoes.md":
            lesson_records[module_title][lesson_title]["notes"] = file.stream.read().decode("utf-8", errors="ignore")
        elif lesson_records[module_title][lesson_title]["attachment_file"] is None:
            lesson_records[module_title][lesson_title]["attachment_file"] = file
            lesson_records[module_title][lesson_title]["attachment_name"] = file_name

    for module_position, module_title in enumerate(sorted(modules_map.keys(), key=natural_key), start=1):
        db.execute(
            """
            INSERT INTO modules (course_id, title, summary, position)
            VALUES (?, ?, ?, ?)
            """,
            (course_id, module_title, f"Imported from {module_title}.", module_position),
        )
        module_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        module_records.append((module_title, module_id))

        for lesson_position, lesson_title in enumerate(sorted(lesson_records[module_title].keys(), key=natural_key), start=1):
            lesson_data = lesson_records[module_title][lesson_title]
            notes = lesson_data["notes"] or f"# {lesson_title}\n\nImported lesson with no markdown notes yet."
            db.execute(
                """
                INSERT INTO lessons (module_id, title, notes, attachment_label, attachment_url, position)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (module_id, lesson_title, notes, None, None, lesson_position),
            )
            lesson_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            attachment_file = lesson_data["attachment_file"]
            if attachment_file and lesson_data["attachment_name"]:
                safe_name = secure_filename(Path(lesson_data["attachment_name"]).name)
                if safe_name:
                    target_dir = lesson_upload_dir(lesson_id)
                    target_path = target_dir / safe_name
                    attachment_file.stream.seek(0)
                    attachment_file.save(target_path)
                    db.execute(
                        """
                        UPDATE lessons
                        SET attachment_label = ?, attachment_url = ?
                        WHERE id = ?
                        """,
                        (lesson_data["attachment_name"], f"/uploads/{lesson_id}/{safe_name}", lesson_id),
                    )

    db.commit()
    return course_id


@app.route("/")
def index():
    db = get_db()
    stats = {
        "courses": db.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"],
        "modules": db.execute("SELECT COUNT(*) AS count FROM modules").fetchone()["count"],
        "lessons": db.execute("SELECT COUNT(*) AS count FROM lessons").fetchone()["count"],
        "notes_words": sum(
            len(row["notes"].split()) for row in db.execute("SELECT notes FROM lessons").fetchall()
        ),
    }
    recent_lessons = db.execute(
        """
        SELECT lessons.id, lessons.title, modules.title AS module_title, courses.title AS course_title
        FROM lessons
        JOIN modules ON lessons.module_id = modules.id
        JOIN courses ON modules.course_id = courses.id
        ORDER BY courses.id DESC, modules.position ASC, lessons.position ASC
        LIMIT 4
        """
    ).fetchall()
    courses = db.execute(
        """
        SELECT
            courses.*,
            COUNT(DISTINCT modules.id) AS module_count,
            COUNT(lessons.id) AS lesson_count
        FROM courses
        LEFT JOIN modules ON modules.course_id = courses.id
        LEFT JOIN lessons ON lessons.module_id = modules.id
        GROUP BY courses.id
        ORDER BY courses.created_at DESC, courses.id DESC
        """
    ).fetchall()
    return render_template("index.html", stats=stats, recent_lessons=recent_lessons, courses=courses)


@app.route("/courses/<int:course_id>")
def course_detail(course_id):
    db = get_db()
    course = query_one_or_404("SELECT * FROM courses WHERE id = ?", (course_id,))
    requested_module_id = request.args.get("module_id", type=int)
    requested_lesson_id = request.args.get("lesson_id", type=int)
    modules = db.execute(
        """
        SELECT
            modules.*,
            COUNT(lessons.id) AS lesson_count
        FROM modules
        LEFT JOIN lessons ON lessons.module_id = modules.id
        WHERE modules.course_id = ?
        GROUP BY modules.id
        ORDER BY modules.position ASC
        """,
        (course_id,),
    ).fetchall()
    selected_module = None
    if modules:
        if requested_module_id:
            selected_module = next((module for module in modules if module["id"] == requested_module_id), modules[0])
        else:
            selected_module = modules[0]
    selected_lesson = None
    all_lessons = db.execute(
        """
        SELECT
            lessons.*,
            modules.course_id
        FROM lessons
        JOIN modules ON lessons.module_id = modules.id
        WHERE modules.course_id = ?
        ORDER BY modules.position ASC, lessons.position ASC
        """,
        (course_id,),
    ).fetchall()
    lessons_by_module = {}
    lesson_lookup = {}
    for lesson in all_lessons:
        lesson_dict = dict(lesson)
        lesson_dict["rendered_notes"] = render_markdown(lesson["notes"])
        lessons_by_module.setdefault(lesson["module_id"], []).append(lesson_dict)
        lesson_lookup[lesson["id"]] = lesson_dict

    if selected_module:
        selected_lessons = lessons_by_module.get(selected_module["id"], [])
        if selected_lessons:
            if requested_lesson_id:
                selected_lesson = next((lesson for lesson in selected_lessons if lesson["id"] == requested_lesson_id), selected_lessons[0])
            else:
                selected_lesson = selected_lessons[0]
    else:
        selected_lessons = []

    modules_payload = []
    for module in modules:
        module_dict = dict(module)
        module_dict["lessons"] = lessons_by_module.get(module["id"], [])
        modules_payload.append(module_dict)

    return render_template(
        "course_detail.html",
        course=course,
        modules=modules,
        modules_payload=modules_payload,
        selected_module=selected_module,
        selected_lessons=selected_lessons,
        selected_lesson=selected_lesson,
    )


@app.route("/courses/import", methods=["POST"])
def import_course():
    uploaded_files = request.files.getlist("course_files")
    if uploaded_files:
        try:
            course_id = import_course_from_upload(uploaded_files)
        except ValueError:
            return redirect(url_for("index"))

        return redirect(url_for("course_detail", course_id=course_id))

    source_path = request.form.get("source_path", "").strip()
    if not source_path:
        return redirect(url_for("index"))

    try:
        course_id = import_course_from_directory(source_path)
    except ValueError:
        return redirect(url_for("index"))

    return redirect(url_for("course_detail", course_id=course_id))


@app.route("/uploads/<int:lesson_id>/<path:filename>")
def uploaded_attachment(lesson_id, filename):
    return send_from_directory(UPLOADS_DIR / str(lesson_id), filename)


@app.route("/courses/<int:course_id>/delete", methods=["POST"])
def delete_course(course_id):
    db = get_db()
    query_one_or_404("SELECT id FROM courses WHERE id = ?", (course_id,))
    lesson_rows = db.execute(
        """
        SELECT lessons.id
        FROM lessons
        JOIN modules ON lessons.module_id = modules.id
        WHERE modules.course_id = ?
        """,
        (course_id,),
    ).fetchall()
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    for lesson in lesson_rows:
        lesson_dir = UPLOADS_DIR / str(lesson["id"])
        if lesson_dir.exists():
            shutil.rmtree(lesson_dir, ignore_errors=True)
    return redirect(url_for("index"))


@app.route("/courses/<int:course_id>/modules/new", methods=["POST"])
def create_module(course_id):
    course = query_one_or_404("SELECT * FROM courses WHERE id = ?", (course_id,))
    values = {
        "title": request.form.get("title", "").strip(),
        "summary": request.form.get("summary", "").strip(),
        "position": request.form.get("position", "").strip(),
    }
    if not values["title"] or not values["position"]:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"error": "All fields are required."}, 400
        return redirect(url_for("course_detail", course_id=course_id))
    try:
        position = int(values["position"])
    except ValueError:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"error": "Position must be a number."}, 400
        return redirect(url_for("course_detail", course_id=course_id))
    db = get_db()
    db.execute(
        """
        INSERT INTO modules (course_id, title, summary, position)
        VALUES (?, ?, ?, ?)
        """,
        (course_id, values["title"], values["summary"] or f"Módulo {values['title']}", position),
    )
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        created_module = query_one_or_404(
            """
            SELECT
                modules.*,
                COUNT(lessons.id) AS lesson_count
            FROM modules
            LEFT JOIN lessons ON lessons.module_id = modules.id
            WHERE modules.id = ?
            GROUP BY modules.id
            """,
            (new_id,),
        )
        module_payload = dict(created_module)
        module_payload["lessons"] = []
        return module_payload

    return redirect(url_for("course_detail", course_id=course_id, module_id=new_id))


@app.route("/modules/<int:module_id>/delete", methods=["POST"])
def delete_module(module_id):
    module = query_one_or_404(
        """
        SELECT modules.id, modules.course_id
        FROM modules
        WHERE modules.id = ?
        """,
        (module_id,),
    )
    db = get_db()
    lesson_rows = db.execute("SELECT id FROM lessons WHERE module_id = ?", (module_id,)).fetchall()
    db.execute("DELETE FROM modules WHERE id = ?", (module_id,))
    db.commit()
    for lesson in lesson_rows:
        lesson_dir = UPLOADS_DIR / str(lesson["id"])
        if lesson_dir.exists():
            shutil.rmtree(lesson_dir, ignore_errors=True)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"deleted_module_id": module_id, "course_id": module["course_id"]}

    return redirect(url_for("course_detail", course_id=module["course_id"]))


@app.route("/courses/<int:course_id>/modules/reorder", methods=["POST"])
def reorder_modules(course_id):
    ordered_ids = request.get_json(silent=True, force=False) or {}
    module_ids = ordered_ids.get("module_ids", [])
    db = get_db()
    existing_modules = db.execute(
        "SELECT id FROM modules WHERE course_id = ? ORDER BY position ASC",
        (course_id,),
    ).fetchall()
    existing_ids = [row["id"] for row in existing_modules]
    if sorted(existing_ids) != sorted(module_ids):
        return {"reordered": False}, 400

    for position, module_id in enumerate(module_ids, start=1):
        db.execute("UPDATE modules SET position = ? WHERE id = ?", (position, module_id))
    db.commit()
    return {"reordered": True}


@app.route("/modules/<int:module_id>/lessons/new", methods=["POST"])
def create_lesson(module_id):
    module = query_one_or_404(
        """
        SELECT modules.*, courses.id AS course_id, courses.title AS course_title
        FROM modules
        JOIN courses ON modules.course_id = courses.id
        WHERE modules.id = ?
        """,
        (module_id,),
    )
    values = {
        "title": request.form.get("title", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "position": request.form.get("position", "").strip(),
    }
    if not values["title"] or not values["notes"] or not values["position"]:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"error": "Title, notes, and position are required."}, 400
        return redirect(url_for("course_detail", course_id=module["course_id"], module_id=module_id))
    try:
        position = int(values["position"])
    except ValueError:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"error": "Position must be a number."}, 400
        return redirect(url_for("course_detail", course_id=module["course_id"], module_id=module_id))
    db = get_db()
    db.execute(
        """
        INSERT INTO lessons (module_id, title, notes, attachment_label, attachment_url, position)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            module_id,
            values["title"],
            values["notes"],
            None,
            None,
            position,
        ),
    )
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    attachment_file = request.files.get("attachment_file")
    attachment_label = request.form.get("attachment_label", "").strip() or None
    if attachment_file and attachment_file.filename:
        saved_name, saved_url = save_attachment_file(attachment_file, new_id)
        if saved_url:
            db.execute(
                """
                UPDATE lessons
                SET attachment_label = ?, attachment_url = ?
                WHERE id = ?
                """,
                (attachment_label or saved_name, saved_url, new_id),
            )
            db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        created_lesson = query_one_or_404(
            """
            SELECT lessons.*
            FROM lessons
            WHERE lessons.id = ?
            """,
            (new_id,),
        )
        lesson_payload = dict(created_lesson)
        lesson_payload["rendered_notes"] = render_markdown(created_lesson["notes"])
        return lesson_payload

    return redirect(url_for("course_detail", course_id=module["course_id"], module_id=module_id, lesson_id=new_id))


@app.route("/lessons/<int:lesson_id>/delete", methods=["POST"])
def delete_lesson(lesson_id):
    lesson = query_one_or_404(
        """
        SELECT lessons.id, lessons.module_id, modules.course_id
        FROM lessons
        JOIN modules ON lessons.module_id = modules.id
        WHERE lessons.id = ?
        """,
        (lesson_id,),
    )
    db = get_db()
    lesson_row = db.execute("SELECT attachment_url FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if lesson_row:
        remove_local_attachment(lesson_row["attachment_url"])
    db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    db.commit()

    lesson_dir = UPLOADS_DIR / str(lesson_id)
    if lesson_dir.exists():
        shutil.rmtree(lesson_dir, ignore_errors=True)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {
            "deleted_lesson_id": lesson_id,
            "module_id": lesson["module_id"],
            "course_id": lesson["course_id"],
        }

    return redirect(url_for("course_detail", course_id=lesson["course_id"], module_id=lesson["module_id"]))


@app.route("/modules/<int:module_id>/lessons/reorder", methods=["POST"])
def reorder_lessons(module_id):
    ordered_ids = request.get_json(silent=True, force=False) or {}
    lesson_ids = ordered_ids.get("lesson_ids", [])
    db = get_db()
    existing_lessons = db.execute(
        "SELECT id FROM lessons WHERE module_id = ? ORDER BY position ASC",
        (module_id,),
    ).fetchall()
    existing_ids = [row["id"] for row in existing_lessons]
    if sorted(existing_ids) != sorted(lesson_ids):
        return {"reordered": False}, 400

    for position, lesson_id in enumerate(lesson_ids, start=1):
        db.execute("UPDATE lessons SET position = ? WHERE id = ?", (position, lesson_id))
    db.commit()
    return {"reordered": True}


@app.route("/lessons/<int:lesson_id>/inline-update", methods=["POST"])
def inline_update_lesson(lesson_id):
    lesson = query_one_or_404(
        """
        SELECT lessons.id, lessons.module_id, modules.course_id
        FROM lessons
        JOIN modules ON lessons.module_id = modules.id
        WHERE lessons.id = ?
        """,
        (lesson_id,),
    )
    title = request.form.get("title", "").strip()
    notes = request.form.get("notes", "").strip()
    attachment_label = request.form.get("attachment_label", "").strip() or None
    attachment_file = request.files.get("attachment_file")

    if title and notes:
        db = get_db()
        existing_attachment = db.execute("SELECT attachment_url FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
        db.execute(
            """
            UPDATE lessons
            SET title = ?, notes = ?, attachment_label = ?, attachment_url = ?
            WHERE id = ?
            """,
            (title, notes, attachment_label, existing_attachment["attachment_url"] if existing_attachment else None, lesson_id),
        )
        if attachment_file and attachment_file.filename:
            if existing_attachment:
                remove_local_attachment(existing_attachment["attachment_url"])
            saved_name, saved_url = save_attachment_file(attachment_file, lesson_id)
            if saved_url:
                db.execute(
                    """
                    UPDATE lessons
                    SET attachment_label = ?, attachment_url = ?
                    WHERE id = ?
                    """,
                    (attachment_label or saved_name, saved_url, lesson_id),
                )
        db.commit()

        updated_lesson = query_one_or_404(
            """
            SELECT lessons.*
            FROM lessons
            WHERE lessons.id = ?
            """,
            (lesson_id,),
        )
        lesson_payload = dict(updated_lesson)
        lesson_payload["rendered_notes"] = render_markdown(updated_lesson["notes"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return lesson_payload

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"error": "Invalid lesson payload."}, 400

    return redirect(
        url_for(
            "course_detail",
            course_id=lesson["course_id"],
            module_id=lesson["module_id"],
            lesson_id=lesson_id,
        )
    )


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        wildcard = f"%{query}%"
        raw_results = get_db().execute(
            """
            SELECT
                lessons.id,
                lessons.module_id,
                lessons.title,
                lessons.notes,
                courses.id AS course_id,
                modules.title AS module_title,
                courses.title AS course_title
            FROM lessons
            JOIN modules ON lessons.module_id = modules.id
            JOIN courses ON modules.course_id = courses.id
            WHERE lessons.title LIKE ?
               OR lessons.notes LIKE ?
               OR modules.title LIKE ?
               OR courses.title LIKE ?
            ORDER BY courses.title ASC, modules.position ASC, lessons.position ASC
            """,
            (wildcard, wildcard, wildcard, wildcard),
        ).fetchall()
        results = [{**dict(row), "excerpt": lesson_excerpt(row["notes"])} for row in raw_results]
    return render_template("search.html", query=query, results=results)


@app.route("/courses/new", methods=["POST"])
def create_course():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    cover_url = request.form.get("cover_url", "").strip() or None
    if not title or not description:
        return redirect(url_for("index"))
    db = get_db()
    db.execute(
        "INSERT INTO courses (title, description, cover_url) VALUES (?, ?, ?)",
        (title, description, cover_url),
    )
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    return redirect(url_for("course_detail", course_id=new_id))


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True)
