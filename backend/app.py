from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import PyPDF2

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

    # Auto login after register
    session["user"] = email

    return jsonify({"message": "Registration successful"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # if already logged in
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
    summary = sentences[:num_sentences]
    return ". ".join(summary)


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

    # Generate summary and questions
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


# ---------------- DASHBOARD ----------------


    user_history = [h for h in history if h["email"] == session["user"]]
    return render_template("dashboard.html", data=user_history)


if __name__ == "__main__":
    app.run(debug=True)
