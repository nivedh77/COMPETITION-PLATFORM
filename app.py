from flask import Flask, render_template, request, redirect
import os
import sqlite3
import tempfile

app = Flask(__name__)

# Determine writeable directories (on Vercel serverless, root is read-only; use /tmp)
IS_VERCEL = bool(os.environ.get("VERCEL"))
if IS_VERCEL or not os.access(".", os.W_OK):
    BASE_DIR = tempfile.gettempdir()
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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

    # Seed sample competition if empty so students have a challenge to select
    cursor.execute("SELECT COUNT(*) FROM competitions")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO competitions (name, description, deadline) VALUES (?, ?, ?)",
            (
                "National Tech Innovation Challenge 2026",
                "Build innovative hardware or software solutions for education and sustainability.",
                "2026-12-31"
            )
        )

    conn.commit()
    conn.close()

# Ensure database and tables exist at module load time (crucial for Vercel serverless)
init_db()

# ---------------- ROUTES ----------------
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "GET":
        return redirect("/")

    role = request.form.get("role")
    if not role:
        return redirect("/")

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

    return "Invalid role", 400

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
    return "✅ Competition created successfully! <br><br><a href='/'>Return to portal</a>"

@app.route("/submit", methods=["POST"])
def submit_project():
    file = request.files.get("project_file")
    if not file or file.filename == "":
        return "No file selected", 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
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

    return "✅ Project submitted successfully! <br><br><a href='/'>Return to portal</a>"

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

    return "✅ Score submitted successfully! <br><br><a href='/leaderboard'>View Leaderboard</a>"

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
