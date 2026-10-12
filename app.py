from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import threading
from datetime import datetime, date, timedelta
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "events.db"
app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret-before-deployment"

# Mutex protects registration-related operations inside this single app process.
registration_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                venue TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT NOT NULL,
                capacity INTEGER NOT NULL CHECK(capacity > 0),
                accent TEXT NOT NULL DEFAULT 'violet'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
                UNIQUE(event_id, student_id),
                UNIQUE(event_id, email)
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            today = date.today()
            seeds = [
                ("AI & Machine Learning Summit", "Technology", "Explore practical AI, generative AI and machine-learning projects with student builders and industry speakers.", "Innovation Hub · Block C", (today + timedelta(days=7)).isoformat(), "10:00 AM", 120, "violet"),
                ("Cybersecurity Capture-the-Flag", "Security", "Team up to solve beginner-friendly security puzzles, web challenges and digital forensics tasks.", "Cyber Lab · Block A", (today + timedelta(days=12)).isoformat(), "02:00 PM", 80, "blue"),
                ("Cloud & DevOps Bootcamp", "Cloud", "Build a deployment pipeline and learn containers, CI/CD, monitoring and cloud fundamentals through guided labs.", "Computer Lab 2", (today + timedelta(days=18)).isoformat(), "09:30 AM", 60, "cyan"),
                ("Campus Startup Pitch Day", "Entrepreneurship", "Present a problem, validate an idea and get feedback on product thinking, prototypes and pitching.", "Seminar Hall", (today + timedelta(days=24)).isoformat(), "11:00 AM", 100, "orange"),
                ("Robotics & IoT Maker Workshop", "Engineering", "Prototype a connected device and learn sensor integration, microcontrollers and real-world IoT use cases.", "Electronics Lab", (today + timedelta(days=31)).isoformat(), "10:30 AM", 45, "green"),
                ("Design Sprint: UI/UX for Good", "Design", "Work in teams to map user journeys, sketch interfaces and turn an idea into a clickable prototype.", "Design Studio", (today + timedelta(days=38)).isoformat(), "01:00 PM", 50, "pink"),
            ]
            conn.executemany("""
                INSERT INTO events(title,category,description,venue,event_date,event_time,capacity,accent)
                VALUES(?,?,?,?,?,?,?,?)
            """, seeds)
        conn.commit()

def event_rows():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.*,
              COUNT(r.id) AS registered,
              e.capacity - COUNT(r.id) AS available
            FROM events e LEFT JOIN registrations r ON e.id = r.event_id
            GROUP BY e.id
            ORDER BY e.event_date, e.event_time
        """).fetchall()
        return [dict(row) for row in rows]

def stats():
    with get_db() as conn:
        return {
            "events": conn.execute("SELECT COUNT(*) FROM events WHERE event_date >= ?", (date.today().isoformat(),)).fetchone()[0],
            "registrations": conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
            "students": conn.execute("SELECT COUNT(DISTINCT student_id) FROM registrations").fetchone()[0],
            "full": conn.execute("""
                SELECT COUNT(*) FROM events e
                WHERE (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.id) >= e.capacity
                  AND e.event_date >= ?
            """, (date.today().isoformat(),)).fetchone()[0]
        }

@app.route("/")
def index():
    events = event_rows()
    upcoming = [e for e in events if e["event_date"] >= date.today().isoformat()]
    return render_template("index.html", events=upcoming, stats=stats(), today=date.today().isoformat())

@app.route("/register/<int:event_id>", methods=["POST"])
def register(event_id):
    student_id = request.form.get("student_id", "").strip().upper()
    student_name = request.form.get("student_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not student_id or not student_name or not email:
        flash("Please complete every field before registering.", "error")
        return redirect(url_for("index") + f"#event-{event_id}")
    if len(student_id) > 40 or len(student_name) > 100 or len(email) > 254 or "@" not in email:
        flash("Please check the student ID, name and email format.", "error")
        return redirect(url_for("index") + f"#event-{event_id}")

    # The lock ensures check-capacity-and-insert is one critical section
    # for threads handled by this Python process. SQLite constraints provide
    # a second layer of protection against duplicate registrations.
    with registration_lock:
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            if event is None:
                conn.rollback()
                flash("That event could not be found.", "error")
            else:
                duplicate = conn.execute(
                    "SELECT id FROM registrations WHERE event_id=? AND (student_id=? OR email=?)",
                    (event_id, student_id, email)
                ).fetchone()
                registered = conn.execute(
                    "SELECT COUNT(*) FROM registrations WHERE event_id=?", (event_id,)
                ).fetchone()[0]
                if duplicate:
                    conn.rollback()
                    flash("This student ID or email is already registered for this event.", "error")
                elif event["event_date"] < date.today().isoformat():
                    conn.rollback()
                    flash("Registration is closed because this event has passed.", "error")
                elif registered >= event["capacity"]:
                    conn.rollback()
                    flash("Sorry, this event is full. No extra seat was allocated.", "error")
                else:
                    conn.execute("""
                        INSERT INTO registrations(event_id, student_id, student_name, email, created_at)
                        VALUES(?,?,?,?,?)
                    """, (event_id, student_id, student_name, email, datetime.now().isoformat(timespec="seconds")))
                    conn.commit()
                    flash(f"You're registered for {event['title']}!", "success")
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("A duplicate registration was blocked by the database.", "error")
        finally:
            conn.close()
    return redirect(url_for("index") + f"#event-{event_id}")

@app.route("/my-registrations", methods=["GET", "POST"])
def my_registrations():
    search_id = ""
    records = []
    if request.method == "POST":
        search_id = request.form.get("student_id", "").strip().upper()
        if search_id:
            with get_db() as conn:
                records = [dict(r) for r in conn.execute("""
                    SELECT r.*, e.title, e.event_date, e.event_time, e.venue
                    FROM registrations r JOIN events e ON e.id=r.event_id
                    WHERE r.student_id=?
                    ORDER BY e.event_date, e.event_time
                """, (search_id,)).fetchall()]
    return render_template("registrations.html", records=records, search_id=search_id)

@app.route("/cancel/<int:registration_id>", methods=["POST"])
def cancel(registration_id):
    student_id = request.form.get("student_id", "").strip().upper()
    with registration_lock, get_db() as conn:
        conn.execute("DELETE FROM registrations WHERE id=? AND student_id=?", (registration_id, student_id))
        conn.commit()
    flash("Cancellation processed. If the record matched your student ID, the seat is now available.", "success")
    return redirect(url_for("my_registrations"))

@app.route("/api/events")
def api_events():
    return jsonify(event_rows())

@app.route("/health")
def health():
    return jsonify({"status": "ok", "database": "connected"})

if __name__ == "__main__":
    init_db()
    print("\\nEvent Registration System is ready.")
    print("Open http://127.0.0.1:5000 in your browser.\\n")
    app.run(debug=True, threaded=True)
