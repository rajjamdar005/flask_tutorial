import os
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.security import generate_password_hash

# Use the project's .env value so a stale shell export cannot override it.
load_dotenv(override=True)

mongo_uri = os.environ.get("MONGO_URI", "").strip()
if not mongo_uri:
    raise RuntimeError(
        "MONGO_URI is not set. Add a raw mongodb:// or mongodb+srv:// URI to .env "
        "or export a valid value in your shell."
    )
if not mongo_uri.startswith(("mongodb://", "mongodb+srv://")):
    raise RuntimeError(
        "MONGO_URI must be a raw mongodb:// or mongodb+srv:// URI, "
        "without Markdown or an https:// prefix. An existing shell variable may "
        "be overriding the value in .env; run 'unset MONGO_URI' to use .env."
    )

app = Flask(__name__)
app.config["MONGO_URI"] = mongo_uri

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
db = client["tutedude"]
users = db["users"]
DATA_FILE = Path(__file__).with_name("data.json")


@app.route("/")
def home():
    now = datetime.now()
    return render_template(
        "index.html",
        current_time=now.strftime("%H:%M:%S"),
        day_of_week=now.strftime("%A"),
        error=None,
        form_data={},
    )


@app.route("/api")
def api():
    try:
        with DATA_FILE.open(encoding="utf-8") as data_file:
            data = json.load(data_file)
    except (OSError, json.JSONDecodeError):
        app.logger.exception("Unable to read API data from %s", DATA_FILE)
        return jsonify({"error": "The API data could not be loaded."}), 500

    if not isinstance(data, list):
        app.logger.error("API data in %s is not a JSON list", DATA_FILE)
        return jsonify({"error": "The API data must be a JSON list."}), 500

    return jsonify(data)


@app.route("/create_account", methods=["POST"])
def create_account():
    name = request.form.get("name", "").strip()
    email_address = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm-password", "")

    if not name or not email_address or not password or not confirm_password:
        return render_template(
            "index.html",
            current_time=datetime.now().strftime("%H:%M:%S"),
            day_of_week=datetime.now().strftime("%A"),
            error="Please fill in all the fields!",
            form_data={"name": name, "email": email_address},
        ), 400

    if password != confirm_password:
        return render_template(
            "index.html",
            current_time=datetime.now().strftime("%H:%M:%S"),
            day_of_week=datetime.now().strftime("%A"),
            error="Passwords do not match!",
            form_data={"name": name, "email": email_address},
        ), 400

    user = {
        "name": name,
        "email": email_address,
        "password": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        users.create_index("email", unique=True)
        users.insert_one(user)
    except DuplicateKeyError:
        error = "An account with this email already exists!"
        status_code = 409
        return render_template(
            "index.html",
            current_time=datetime.now().strftime("%H:%M:%S"),
            day_of_week=datetime.now().strftime("%A"),
            error=error,
            form_data={"name": name, "email": email_address},
        ), status_code
    except PyMongoError:
        app.logger.exception("Unable to save the new account")
        return render_template(
            "index.html",
            current_time=datetime.now().strftime("%H:%M:%S"),
            day_of_week=datetime.now().strftime("%A"),
            error="The account could not be created right now. Please try again.",
            form_data={"name": name, "email": email_address},
        ), 503

    return redirect(url_for("submission_success"))


@app.route("/success")
def submission_success():
    return render_template("submit.html")


if __name__ == "__main__":
    app.run(debug=True)
