from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Notes App Running"

app.run(debug=True)
