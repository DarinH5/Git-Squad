import json
import os
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
DB_FILE = "database.json"

def load_data():
    """Reads data from the JSON file backend."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []

def save_data(data):
    """Writes data to the JSON file backend."""
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Simple, modern UI using clean HTML & CSS (No frameworks needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Web UI Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 600px;
            background: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        h2 { margin-top: 0; color: #111; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px; }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 6px;
            box-sizing: border-box;
            font-size: 14px;
        }
        textarea { height: 100px; resize: vertical; }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            width: 100%;
        }
        button:hover { background-color: #0056b3; }
        .notes-section { margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }
        .note-card {
            background: #fafafa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 0 6px 6px 0;
        }
        .note-title { font-weight: bold; margin-bottom: 5px; color: #222; }
        .note-content { font-size: 14px; color: #555; white-space: pre-wrap; }
        .empty-state { text-align: center; color: #888; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Submit New Entry</h2>
        <form method="POST" action="/add">
            <div class="form-group">
                <label for="title">Title</label>
                <input type="text" id="title" name="title" required placeholder="Enter a title...">
            </div>
            <div class="form-group">
                <label for="content">Content Description</label>
                <textarea id="content" name="content" required placeholder="Type something here..."></textarea>
            </div>
            <button type="submit">Save to JSON Backend</button>
        </form>

        <div class="notes-section">
            <h2>Saved Entries (From JSON)</h2>
            {% if entries %}
                {% for entry in entries %}
                    <div class="note-card">
                        <div class="note-title">{{ entry.title }}</div>
                        <div class="note-content">{{ entry.content }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <p class="empty-state">No entries saved yet. Submit the form above!</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    # Load all stored logs/entries reverse chronological order
    entries = list(reversed(load_data()))
    return render_template_string(HTML_TEMPLATE, entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():
    title = request.form.get('title')
    content = request.form.get('content')
    
    if title and content:
        current_data = load_data()
        current_data.append({
            "title": title,
            "content": content
        })
        save_data(current_data)
        
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
