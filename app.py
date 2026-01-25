from flask import Flask, render_template, request
import os
import sqlite3

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            deadline TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            title TEXT,
            filename TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER,
            score INTEGER,
            feedback TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---------------- ROUTES ----------------
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/dashboard", methods=["POST"])
def dashboard():
    role = request.form["role"]

    if role == "Student":
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM competitions")
        competitions = cursor.fetchall()

        cursor.execute("""
            SELECT submissions.title, competitions.name AS competition,
                   scores.score, scores.feedback
            FROM submissions
            JOIN competitions ON submissions.competition_id = competitions.id
            LEFT JOIN scores ON scores.submission_id = submissions.id
        """)
        status = cursor.fetchall()

        conn.close()
        return render_template("student.html", competitions=competitions, status=status)

    if role == "Judge":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT submissions.id, submissions.title, competitions.name AS competition
            FROM submissions
            JOIN competitions ON submissions.competition_id = competitions.id
        """)
        submissions = cursor.fetchall()
        conn.close()
        return render_template("judge.html", submissions=submissions)

    if role == "School":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM competitions")
        competitions = cursor.fetchall()
        conn.close()
        return render_template("school.html", competitions=competitions)

    return "Invalid role"

@app.route("/create_competition", methods=["POST"])
def create_competition():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO competitions (name, description, deadline) VALUES (?, ?, ?)",
        (request.form["name"], request.form["description"], request.form["deadline"])
    )
    conn.commit()
    conn.close()
    return "✅ Competition created successfully!"

@app.route("/submit", methods=["POST"])
def submit_project():
    file = request.files["project_file"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO submissions (competition_id, title, filename) VALUES (?, ?, ?)",
        (request.form["competition_id"], request.form["title"], file.filename)
    )
    conn.commit()
    conn.close()

    return "✅ Project submitted successfully!"

@app.route("/score", methods=["POST"])
def score_project():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scores (submission_id, score, feedback) VALUES (?, ?, ?)",
        (request.form["submission_id"], request.form["score"], request.form["feedback"])
    )
    conn.commit()
    conn.close()

    return "✅ Score submitted successfully!"

@app.route("/leaderboard")
def leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT competitions.name AS competition,
               submissions.title AS project,
               MAX(scores.score) AS score
        FROM scores
        JOIN submissions ON scores.submission_id = submissions.id
        JOIN competitions ON submissions.competition_id = competitions.id
        GROUP BY submissions.id
        ORDER BY score DESC
    """)
    leaderboard = cursor.fetchall()
    conn.close()

    return render_template("leaderboard.html", leaderboard=leaderboard)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
