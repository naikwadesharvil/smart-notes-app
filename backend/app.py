from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import os
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "smart_notes_secret"

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

users = []
history = []


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    data = request.json
    email = data.get("email")
    password = data.get("password")

    users.append({
        "email": email,
        "password": generate_password_hash(password)
    })

    # auto login after register
    session["user"] = email
    return jsonify({"message": "Registration successful"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("upload"))

    if request.method == "GET":
        return render_template("login.html")

    data = request.json
    email = data.get("email")
    password = data.get("password")

    for user in users:
        if user["email"] == email and check_password_hash(user["password"], password):
            session["user"] = email
            return jsonify({"message": "Login successful"})

    return jsonify({"message": "Invalid email or password"})


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------------- SUMMARY FUNCTION ----------------
def generate_summary(text, num_sentences=5):
    sentences = text.split(".")
    return ". ".join(sentences[:num_sentences])


def generate_questions(text):
    sentences = text.split(".")
    questions = []
    for i in range(min(5, len(sentences))):
        q = f"Q{i+1}. Explain: {sentences[i].strip()}?"
        questions.append(q)
    return questions


# ---------------- UPLOAD ----------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files["file"]
    branch = request.form.get("branch")
    subject = request.form.get("subject")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Read TXT or PDF
    if file.filename.endswith(".pdf"):
        text = ""
        pdf = PyPDF2.PdfReader(filepath)
        for page in pdf.pages:
            text += page.extract_text()
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

    summary = generate_summary(text)
    questions = generate_questions(text)

    history.append({
        "email": session["user"],
        "branch": branch,
        "subject": subject,
        "summary": summary,
        "questions": questions
    })

    return jsonify({
        "branch": branch,
        "subject": subject,
        "summary": summary,
        "questions": questions
    })


# ---------------- DOWNLOAD PDF ----------------
@app.route("/download_pdf")
def download_pdf():
    if "user" not in session:
        return redirect(url_for("login"))

    if len(history) == 0:
        return "No data to download"

    last = history[-1]

    file_path = "result.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)
    text = c.beginText(40, 750)

    text.textLine(f"Branch: {last['branch']}")
    text.textLine(f"Subject: {last['subject']}")
    text.textLine("")
    text.textLine("SUMMARY:")
    text.textLine("-------------------------")

    for line in last["summary"].split("\n"):
        text.textLine(line)

    text.textLine("")
    text.textLine("QUESTIONS:")
    text.textLine("-------------------------")

    for q in last["questions"]:
        text.textLine(q)

    c.drawText(text)
    c.save()

    return send_file(file_path, as_attachment=True)


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    user_history = [h for h in history if h["email"] == session["user"]]
    return render_template("dashboard.html", data=user_history)


if __name__ == "__main__":
    app.run(debug=True)
