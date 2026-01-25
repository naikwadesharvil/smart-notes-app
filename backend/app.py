from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

users = []

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/")
def home():
    return "Smart Notes App Running"

@app.route("/register", methods=["POST"])
def register():
    ...

@app.route("/login", methods=["POST"])
def login():
    ...

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"})

    file = request.files["file"]
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))

    return jsonify({"message": "File uploaded successfully!"})

if __name__ == "__main__":
    app.run(debug=True)
