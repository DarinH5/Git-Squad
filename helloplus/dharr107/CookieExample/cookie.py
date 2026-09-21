"""Minimal cookie-based authentication example.

Run with:  python cookie.py
Set COOKIE_SECRET_KEY in production.
"""

import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from flask import Flask, jsonify, request


app = Flask(__name__)
app.config.update(
	SECRET_KEY=os.environ.get("COOKIE_SECRET_KEY", secrets.token_hex(32)),
	SESSION_COOKIE_NAME="auth_token",
	SESSION_COOKIE_HTTPONLY=True,
	SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
	SESSION_COOKIE_SAMESITE="Lax",
	PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# Replace this with a database in a real application.
users = {}
tokens = {}


def hash_password(password, salt=None):
	salt = salt or os.urandom(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
	return salt.hex() + ":" + digest.hex()


def valid_password(password, stored):
	salt, expected = stored.split(":", 1)
	actual = hashlib.pbkdf2_hmac(
		"sha256", password.encode(), bytes.fromhex(salt), 310_000
	).hex()
	return hmac.compare_digest(actual, expected)


def current_user():
	token = request.cookies.get(app.config["SESSION_COOKIE_NAME"])
	return tokens.get(token) if token else None


@app.post("/register")
def register():
	data = request.get_json(silent=True) or {}
	username, password = data.get("username"), data.get("password")
	if not isinstance(username, str) or not isinstance(password, str) or len(password) < 8:
		return jsonify(error="username and a password of at least 8 characters are required"), 400
	if username in users:
		return jsonify(error="username already exists"), 409
	users[username] = hash_password(password)
	return jsonify(message="registered"), 201


@app.post("/login")
def login():
	data = request.get_json(silent=True) or {}
	username, password = data.get("username"), data.get("password", "")
	if username not in users or not valid_password(password, users[username]):
		return jsonify(error="invalid credentials"), 401
	token = secrets.token_urlsafe(32)
	tokens[token] = username
	response = jsonify(message="logged in")
	response.set_cookie(
		app.config["SESSION_COOKIE_NAME"], token,
		max_age=int(app.permanent_session_lifetime.total_seconds()),
		httponly=True, secure=app.config["SESSION_COOKIE_SECURE"], samesite="Lax",
	)
	return response


@app.post("/logout")
def logout():
	token = request.cookies.get(app.config["SESSION_COOKIE_NAME"])
	if token:
		tokens.pop(token, None)
	response = jsonify(message="logged out")
	response.delete_cookie(app.config["SESSION_COOKIE_NAME"])
	return response


@app.get("/me")
def me():
	username = current_user()
	if not username:
		return jsonify(error="authentication required"), 401
	return jsonify(username=username)


if __name__ == "__main__":
	app.run(debug=False)
