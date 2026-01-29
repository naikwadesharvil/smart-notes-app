from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import nltk
import re
from nltk.tokenize import sent_tokenize

nltk.download("punkt")

app = Flask(__name__)
app.secret_key = "smart_notes_secret"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smartnotes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120))
    branch = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    summary = db.Column(db.Text)
    questions = db.Column(db.Text)


# ---------------- HELPERS ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_summary(text, num_sentences=5):
    sentences = sent_tokenize(text)
    return " ".join(sentences[:num_sentences])


def generate_questions(text):
    text = re.sub(r'\s+', ' ', text)
    sentences = sent_tokenize(text)

    questions = []
    seen = set()

    for s in sentences:
        s = re.sub(r'[^A-Za-z0-9 ,.]+', '', s).strip()

        if len(s) < 25:
            continue

        if s in seen:
            continue
        seen.add(s)

        q = f"Explain in detail: {s}?"
        questions.append(q)

        if len(questions) == 5:
            break

    return questions


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# -------- REGISTER --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    data = request.json
    email = data.get("email")
    password = data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"})

    hashed = generate_password_hash(password)
    new_user = User(email=email, password=hashed)

    db.session.add(new_user)
    db.session.commit()

    session["user"] = email
    return jsonify({"message": "Registration successful"})


# -------- LOGIN --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("upload"))

    if request.method == "GET":
        return render_template("login.html")

    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        session["user"] = email
        return jsonify({"message": "Login successful"})

    return jsonify({"message": "Invalid email or password"})


# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# -------- UPLOAD --------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("file")
    branch = request.form.get("branch")
    subject = request.form.get("subject")

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF and TXT files allowed"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    text = ""

    try:
        if file.filename.endswith(".pdf"):
            pdf = PyPDF2.PdfReader(filepath)
            for page in pdf.pages[:10]:   # limit pages for large PDF
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        else:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

    except Exception as e:
        print("File error:", e)
        return jsonify({"error": "Failed to read file"}), 500

    if len(text.strip()) == 0:
        return jsonify({"error": "File contains no readable text"}), 400

    sentences = sent_tokenize(text)
    limited_text = " ".join(sentences[:30])

    summary = generate_summary(limited_text)
    questions = generate_questions(limited_text)

    new_history = History(
        email=session["user"],
        branch=branch,
        subject=subject,
        summary=summary,
        questions="||".join(questions)
    )

    db.session.add(new_history)
    db.session.commit()

    return jsonify({
        "branch": branch,
        "subject": subject,
        "summary": summary,
        "questions": questions
    })


# -------- DOWNLOAD PDF --------
@app.route("/download_pdf")
def download_pdf():
    if "user" not in session:
        return redirect(url_for("login"))

    last = History.query.filter_by(email=session["user"]).order_by(History.id.desc()).first()

    if not last:
        return "No data available"

    file_path = "result.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)
    text = c.beginText(40, 750)

    text.textLine(f"Branch: {last.branch}")
    text.textLine(f"Subject: {last.subject}")
    text.textLine("")
    text.textLine("SUMMARY:")
    text.textLine("----------------")

    for line in last.summary.split("\n"):
        text.textLine(line)

    text.textLine("")
    text.textLine("QUESTIONS:")
    text.textLine("----------------")

    for q in last.questions.split("||"):
        text.textLine(q)

    c.drawText(text)
    c.save()

    return send_file(file_path, as_attachment=True)


# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    data = History.query.filter_by(email=session["user"]).all()
    return render_template("dashboard.html", data=data)


# -------- CREATE DB --------
with app.app_context():
    db.create_all()


# -------- RUN --------
if __name__ == "__main__":
    app.run(debug=True)
