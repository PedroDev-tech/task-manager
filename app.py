from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from i18n import LANGUAGES, DEFAULT_LANGUAGE, DATE_FORMATS, translate
import os
import uuid
from werkzeug.utils import secure_filename
from flask import send_from_directory

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(24).hex()
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads"))
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", str(5 * 1024 * 1024)))
VALID_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "txt", "doc", "docx", "zip"}

SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "0").lower() not in ("0", "false", "no")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", SMTP_USERNAME or "admin@localhost")
MAIL_MODE = os.environ.get("MAIL_MODE", "console").lower()

db = SQLAlchemy(app)

VALID_LANGUAGES = {code for code, _ in LANGUAGES}
VALID_TAGS_SEPARATOR = ","
VALID_PRIORITIES = ("alta", "media", "baixa")
VALID_STATUSES = ("pendente", "concluida")
PER_PAGE = 8


def get_lang():
    return session.get("lang", DEFAULT_LANGUAGE)


def t(key, **kwargs):
    text = translate(get_lang(), key)
    return text.format(**kwargs) if kwargs else text


@app.before_request
def apply_language():
    lang = request.args.get("lang")
    if lang in VALID_LANGUAGES:
        session["lang"] = lang


@app.context_processor
def inject_i18n():
    def lang_url(target):
        args = request.args.to_dict()
        args["lang"] = target
        return url_for(request.endpoint, **(request.view_args or {}), **args)

    return {
        "t": t,
        "lang": get_lang(),
        "languages": LANGUAGES,
        "lang_url": lang_url,
        "date_format": DATE_FORMATS.get(get_lang(), DATE_FORMATS[DEFAULT_LANGUAGE]),
    }


def parse_due_date(value):
    """Return (date, ok). Empty value -> (None, True); invalid -> (None, False)."""
    if not value:
        return None, True
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), True
    except (ValueError, TypeError):
        return None, False



def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in VALID_EXTENSIONS


def parse_tags(value):
    if not value:
        return []
    names = []
    seen = set()
    for raw in value.split(","):
        name = raw.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def get_or_create_tag(name):
    tag = Tag.query.filter_by(name=name).first()
    if tag is None:
        tag = Tag(name=name)
        db.session.add(tag)
        db.session.flush()
    return tag


def save_attachments(task, files):
    saved = 0
    for f in files or []:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            continue
        original = f.filename
        safe = secure_filename(original)
        unique = f"{uuid.uuid4().hex}_{safe or 'file'}"
        f.save(os.path.join(app.config["UPLOAD_FOLDER"], unique))
        db.session.add(Attachment(task_id=task.id, filename=original, stored_name=unique))
        saved += 1
    return saved


def send_overdue_emails():
    import smtplib
    from email.message import EmailMessage

    host = SMTP_HOST
    port = SMTP_PORT
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    use_tls = SMTP_USE_TLS
    recipient = NOTIFY_EMAIL
    if MAIL_MODE == "smtp":
        if not recipient:
            return False, "Destinatario ausente (NOTIFY_EMAIL)."
        if not host:
            return False, "SMTP nao configurado (SMTP_HOST ausente)."

    today = date.today()
    overdue = Task.query.filter(Task.due_date < today, Task.status != "concluida").all()
    if not overdue:
        return True, "Nenhuma tarefa atrasada."

    lines = ["Tarefas atrasadas:", ""]
    for task in overdue:
        lines.append(f"- {task.title} — prazo {task.due_date.strftime('%Y-%m-%d')} ({task.priority})")
    body = "\n".join(lines)

    if MAIL_MODE != "smtp":
        print("NOTIFICACAO (console):\n" + body)
        return True, f"Modo console: {len(overdue)} tarefa(s) atrasada(s) registrada(s); configure SMTP/MAIL_MODE=smtp para envio real."

    msg = EmailMessage()
    msg["Subject"] = "Tarefas atrasadas - Task Manager"
    msg["From"] = username or "task-manager@localhost"
    msg["To"] = recipient
    msg.set_content(body)

    try:
        if use_tls:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        return True, f"E-mail enviado para {recipient} ({len(overdue)} tarefa(s))."
    except Exception as exc:
        return False, f"Falha ao enviar e-mail: {exc}"

def task_stats():
    """Compute all dashboard counters in a single aggregated query."""
    today = date.today()
    row = db.session.query(
        db.func.count(Task.id),
        db.func.sum(db.case((Task.status == "pendente", 1), else_=0)),
        db.func.sum(db.case((Task.status == "concluida", 1), else_=0)),
        db.func.sum(
            db.case(
                (db.and_(Task.due_date.isnot(None), Task.due_date < today, Task.status != "concluida"), 1),
                else_=0,
            )
        ),
    ).one()
    total, pending, done, overdue = (value or 0 for value in row)
    return {"total": total, "pending": pending, "done": done, "overdue": overdue}


task_tags = db.Table(
    "task_tags",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)


class Attachment(db.Model):
    __tablename__ = "attachments"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    priority = db.Column(db.String(10), nullable=False, default="media")
    status = db.Column(db.String(10), nullable=False, default="pendente")
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    tags = db.relationship("Tag", secondary=task_tags, backref=db.backref("tasks", lazy="dynamic"))
    attachments = db.relationship("Attachment", backref="task", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < date.today() and self.status != "concluida")

    @property
    def is_due_today(self):
        return self.due_date == date.today() and self.status != "concluida"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_overdue": self.is_overdue,
            "is_due_today": self.is_due_today,
            "tags": [tag.name for tag in self.tags],
            "attachments": [{"id": a.id, "filename": a.filename, "url": f"/uploads/{a.stored_name}"} for a in self.attachments],
        }


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/tasks")
def tasks():
    status_filter = request.args.get("status", "todas")
    priority_filter = request.args.get("priority", "todas")
    tag_filter = request.args.get("tag", "").strip()
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "created_desc")

    query = Task.query

    if status_filter == "pendentes":
        query = query.filter(Task.status == "pendente")
    elif status_filter == "concluidas":
        query = query.filter(Task.status == "concluida")
    elif status_filter == "atrasadas":
        query = query.filter(Task.due_date < date.today(), Task.status != "concluida")
    elif status_filter == "hoje":
        query = query.filter(Task.due_date == date.today(), Task.status != "concluida")

    if priority_filter in VALID_PRIORITIES:
        query = query.filter(Task.priority == priority_filter)
    if tag_filter:
        query = query.filter(Task.tags.any(Tag.name == tag_filter))

    if search:
        query = query.filter(
            db.or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
        )

    sort_map = {
        "created_desc": Task.created_at.desc(),
        "created_asc": Task.created_at.asc(),
        "due_asc": Task.due_date.asc().nullslast(),
        "due_desc": Task.due_date.desc().nullslast(),
        "priority_desc": db.case(
            (Task.priority == "alta", 1),
            (Task.priority == "media", 2),
            (Task.priority == "baixa", 3),
        ),
    }
    query = query.order_by(sort_map.get(sort, Task.created_at.desc()), Task.id.desc())

    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    return render_template(
        "tasks.html",
        tasks=pagination.items,
        pagination=pagination,
        **task_stats(),
        status_filter=status_filter,
        priority_filter=priority_filter,
        tag_filter=tag_filter,
        search=search,
        sort=sort,
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash(t("flash.title_required"), "error")
            return redirect(url_for("create"))

        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "media")
        if priority not in VALID_PRIORITIES:
            priority = "media"
        status = request.form.get("status", "pendente")
        if status not in VALID_STATUSES:
            status = "pendente"

        due_date, ok = parse_due_date(request.form.get("due_date", ""))
        if not ok:
            flash(t("flash.invalid_date"), "error")
            return redirect(url_for("create"))

        task = Task(
            title=title,
            description=description,
            priority=priority,
            status=status,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.flush()
        for name in parse_tags(request.form.get("tags", "")):
            task.tags.append(get_or_create_tag(name))
        db.session.commit()
        save_attachments(task, request.files.getlist("attachments"))
        db.session.commit()
        flash(t("flash.created"), "success")
        return redirect(url_for("tasks"))

    return render_template("form.html", task=None, action="create")


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit(task_id):
    task = Task.query.get_or_404(task_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash(t("flash.title_required"), "error")
            return redirect(url_for("edit", task_id=task_id))

        task.title = title
        task.description = request.form.get("description", "").strip()

        priority = request.form.get("priority", task.priority)
        if priority in VALID_PRIORITIES:
            task.priority = priority
        status = request.form.get("status", task.status)
        if status in VALID_STATUSES:
            task.status = status

        due_date, ok = parse_due_date(request.form.get("due_date", ""))
        if not ok:
            flash(t("flash.invalid_date"), "error")
            return redirect(url_for("edit", task_id=task_id))
        task.due_date = due_date

        task.tags = []
        for name in parse_tags(request.form.get("tags", "")):
            task.tags.append(get_or_create_tag(name))

        task.updated_at = datetime.now()
        save_attachments(task, request.files.getlist("attachments"))
        db.session.commit()
        flash(t("flash.updated"), "success")
        return redirect(url_for("tasks"))

    return render_template("form.html", task=task, action="edit")


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = "concluida" if task.status == "pendente" else "pendente"
    task.updated_at = datetime.now()
    db.session.commit()
    status_key = "status.done" if task.status == "concluida" else "status.pending"
    flash(t("flash.marked", status=t(status_key)), "success")
    return redirect(request.referrer or url_for("tasks"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    task = Task.query.get_or_404(task_id)
    for att in task.attachments:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], att.stored_name))
        except OSError:
            pass
    db.session.delete(task)
    db.session.commit()
    flash(t("flash.deleted"), "success")
    return redirect(url_for("tasks"))


@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return {"tasks": [task.to_dict() for task in tasks]}


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def api_task(task_id):
    task = Task.query.get_or_404(task_id)
    return task.to_dict()


@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return {"error": "O campo 'title' é obrigatorio."}, 400

    priority = data.get("priority", "media")
    if priority not in VALID_PRIORITIES:
        return {"error": f"priority deve ser um de {VALID_PRIORITIES}."}, 400
    status = data.get("status", "pendente")
    if status not in VALID_STATUSES:
        return {"error": f"status deve ser um de {VALID_STATUSES}."}, 400

    due_date, ok = parse_due_date(data.get("due_date"))
    if not ok:
        return {"error": "due_date deve estar no formato YYYY-MM-DD."}, 400

    task = Task(
        title=title,
        description=data.get("description", "") or "",
        priority=priority,
        status=status,
        due_date=due_date,
    )
    db.session.add(task)
    db.session.flush()
    for name in parse_tags(data.get("tags", "") if isinstance(data.get("tags"), str) else ",".join(data.get("tags") or [])):
        task.tags.append(get_or_create_tag(name))
    db.session.commit()
    return task.to_dict(), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def api_update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return {"error": "O título é obrigatório."}, 400
        task.title = title
    if "description" in data:
        task.description = data.get("description") or ""
    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return {"error": "Prioridade inválida."}, 400
        task.priority = data["priority"]
    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return {"error": "Status inválido."}, 400
        task.status = data["status"]
    if "due_date" in data:
        due_date, ok = parse_due_date(data.get("due_date"))
        if not ok:
            return {"error": "Data inválida. Use o formato YYYY-MM-DD."}, 400
        task.due_date = due_date
    if "tags" in data:
        task.tags = []
        raw = data["tags"]
        names = raw if isinstance(raw, list) else str(raw).split(",")
        for name in parse_tags(",".join(names)):
            task.tags.append(get_or_create_tag(name))

    task.updated_at = datetime.now()
    db.session.commit()
    return task.to_dict()


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return {"deleted": task_id}




@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.png", mimetype="image/png")


@app.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    task_id = attachment.task_id
    try:
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], attachment.stored_name))
    except OSError:
        pass
    db.session.delete(attachment)
    db.session.commit()
    flash(t("flash.attachment_deleted"), "success")
    return redirect(url_for("edit", task_id=task_id))


@app.route("/notify/overdue", methods=["POST", "GET"])
def notify_overdue():
    ok, message = send_overdue_emails()
    flash(message, "success" if ok else "error")
    return redirect(url_for("tasks"))

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)



def send_reminder_emails(days_before=1):
    today = date.today()
    upcoming = today + timedelta(days=days_before)
    due_soon = Task.query.filter(Task.due_date == upcoming, Task.status != "concluida").all()
    overdue = Task.query.filter(Task.due_date < today, Task.status != "concluida").all()
    tasks = due_soon + overdue
    if not tasks:
        return True, "Nenhuma tarefa para lembrete."

    lines = ["Lembretes de tarefas:", ""]
    if due_soon:
        lines.append("Vencem em breve:")
        for task in due_soon:
            lines.append(f"- {task.title} — prazo {task.due_date.strftime('%Y-%m-%d')} ({task.priority})")
    if overdue:
        lines.append("")
        lines.append("Atrasadas:")
        for task in overdue:
            lines.append(f"- {task.title} — prazo {task.due_date.strftime('%Y-%m-%d')} ({task.priority})")
    body = "\n".join(lines)

    if MAIL_MODE != "smtp":
        print("LEMBRETE (console):\n" + body)
        return True, f"Modo console: {len(tasks)} lembrete(s) registrado(s)."

    import smtplib
    from email.message import EmailMessage
    host = SMTP_HOST
    port = SMTP_PORT
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    use_tls = SMTP_USE_TLS
    recipient = NOTIFY_EMAIL
    if not recipient:
        return False, "Destinatario ausente (NOTIFY_EMAIL)."
    if not host:
        return False, "SMTP nao configurado (SMTP_HOST ausente)."

    msg = EmailMessage()
    msg["Subject"] = "Lembretes de tarefas - Task Manager"
    msg["From"] = username or "task-manager@localhost"
    msg["To"] = recipient
    msg.set_content(body)

    try:
        if use_tls:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        return True, f"E-mail de lembrete enviado para {recipient} ({len(tasks)} tarefa(s))."
    except Exception as exc:
        return False, f"Falha ao enviar lembrete: {exc}"



@app.route("/reminders", methods=["GET", "POST"])
def reminders():
    if request.method == "POST":
        days = request.form.get("days", 1, type=int) or 1
        ok, message = send_reminder_emails(days)
        flash(message, "success" if ok else "error")
        return redirect(url_for("reminders"))
    return render_template("reminders.html", mail_mode=os.environ.get("MAIL_MODE", "console").lower())


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
