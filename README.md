# Campusly — Event / Workshop Registration System

A polished synchronization-based OS & CN product using Flask, SQLite, Python threads, and a responsive HTML/CSS/JavaScript interface.

## Features
- Responsive event discovery dashboard with search and category filters
- Upcoming sample events seeded automatically with dates relative to the day the database is first created
- Registration modal with student ID, name, and email
- Mutex-protected capacity check + registration insert (`threading.Lock`)
- SQLite transaction and database uniqueness constraints as an additional safeguard
- Duplicate registration prevention by student ID or email per event
- Capacity meter and dashboard statistics
- Lookup registrations by student ID
- Cancellation reopens a seat
- JSON event endpoint (`/api/events`) and health endpoint (`/health`)
- Responsive design for desktop, tablet and mobile

## Requirements
- Python 3.10 or newer recommended
- Internet connection only for the optional Google Fonts loaded by the browser; the app itself does not need an API key.

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `EventRegistrationSystem` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment (recommended):
   ```powershell
   py -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run:
   ```bat
   .venv\\Scripts\\activate.bat
   ```
5. Install dependencies:
   ```powershell
   py -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   py app.py
   ```
7. Open **http://127.0.0.1:5000** in Chrome or Edge.

## How to demonstrate
1. On Discover events, select Register for event.
2. Enter a student name, unique student ID, and email.
3. Try the same student ID/email for the same event again: the duplicate should be rejected.
4. Register unique students until the event fills: further registrations must be rejected.
5. Open My registrations, search by student ID, then cancel one registration.
6. Return to Discover events and confirm that one seat is available again.

## OS concepts for viva
- Shared resource: event capacity and registration records.
- Race condition: concurrent requests may both read the last available seat before either writes.
- Critical section: check current registration count and insert the registration.
- Mutex: `threading.Lock()` serializes this critical section within one Python process.
- Additional protection: SQLite `BEGIN IMMEDIATE` transactions and unique constraints.
- Limitation: an in-process Python lock does not coordinate separate server processes or multiple machines. For production multi-worker deployments, rely on database transactions/constraints and suitable transaction design.

## Important notes
- This is a student prototype, not a production deployment.
- The secret key in `app.py` is a development placeholder. Change it before deployment.
- Registration data is stored in `events.db` next to `app.py`. Do not delete this file unless you intend to reset all records.
- Demo events are sample events, not verified real-world event listings.
- Run only on your own computer for the class demo; do not expose the development server publicly.
