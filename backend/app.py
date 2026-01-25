from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)   # 👈 this line is very important

@app.route("/")
def home():
    return "Smart Notes App Running"

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    print("New User Registered:")
    print(name, email, password)

    return jsonify({"message": "User registered successfully!"})

if __name__ == "__main__":
    app.run(debug=True)
