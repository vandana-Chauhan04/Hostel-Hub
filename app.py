import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

app = Flask(__name__)
app.secret_key = "hostelhub-secret-key"

# ---------------- DATABASE CONFIGURATION ----------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE = os.path.join(INSTANCE_DIR, "hostel.db")

os.makedirs(INSTANCE_DIR, exist_ok=True)


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


# ---------------- DROPDOWN DEFAULT OPTIONS ----------------

DEFAULT_OPTIONS = {
    "room_type": [
        "Single Seater",
        "Double Seater",
        "Triple Seater",
        "Four Seater",
        "Custom"
    ],

    "course": [
        "B.Tech",
        "BCA",
        "MCA",
        "MBA",
        "Other"
    ],

    "payment_method": [
        "Cash",
        "UPI",
        "Bank Transfer",
        "Card"
    ],

    "payment_status": [
        "Paid",
        "Pending",
        "Failed"
    ],

    "complaint_status": [
        "Pending",
        "In Progress",
        "Resolved"
    ]
}


CATEGORY_NAMES = {
    "room_type": "Room Type",
    "course": "Course",
    "payment_method": "Payment Method",
    "payment_status": "Payment Status",
    "complaint_status": "Complaint Status"
}


# Used to check whether a dropdown option is already being used
OPTION_USAGE_TABLES = {
    "room_type": ("rooms", "room_type"),
    "course": ("students", "course"),
    "payment_method": ("payments", "payment_method"),
    "payment_status": ("payments", "status"),
    "complaint_status": ("complaints", "status")
}


# ---------------- CREATE DATABASE TABLES ----------------

def init_db():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            course TEXT,
            room_id INTEGER,
            admission_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            monthly_fee REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL NOT NULL,
            payment_date TEXT,
            payment_method TEXT,
            status TEXT DEFAULT 'Paid',
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            complaint_date TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            phone TEXT,
            salary REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            hostel_name TEXT,
            hostel_address TEXT,
            contact_number TEXT
        )
    """)

    # New dropdown options table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dropdown_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            option_value TEXT NOT NULL,
            UNIQUE(category, option_value)
        )
    """)

    # Default hostel settings
    cursor.execute("""
        INSERT OR IGNORE INTO settings
        (id, hostel_name, hostel_address, contact_number)
        VALUES (
            1,
            'Hostel Management System',
            '',
            ''
        )
    """)

    # Insert default dropdown options
    # Existing options will not be duplicated
    for category, options in DEFAULT_OPTIONS.items():

        for option in options:

            cursor.execute("""
                INSERT OR IGNORE INTO dropdown_options
                (category, option_value)
                VALUES (?, ?)
            """, (category, option))

    db.commit()
    db.close()


# ---------------- GET DROPDOWN OPTIONS ----------------

def get_options(category):

    db = get_db()

    rows = db.execute("""
        SELECT option_value
        FROM dropdown_options
        WHERE category = ?
        ORDER BY id
    """, (category,)).fetchall()

    db.close()

    return [row["option_value"] for row in rows]


# ======================================================
#                       DASHBOARD
# ======================================================

@app.route("/")
@app.route("/dashboard")
def dashboard():

    db = get_db()

    total_students = db.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    total_rooms = db.execute(
        "SELECT COUNT(*) FROM rooms"
    ).fetchone()[0]

    total_payments = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Paid'
    """).fetchone()[0]

    pending_complaints = db.execute("""
        SELECT COUNT(*)
        FROM complaints
        WHERE status = 'Pending'
    """).fetchone()[0]

    db.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_rooms=total_rooms,
        total_payments=total_payments,
        pending_complaints=pending_complaints
    )


# ======================================================
#                       STUDENTS
# ======================================================

@app.route("/students", methods=["GET", "POST"])
def students():

    db = get_db()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        course = request.form.get("course", "").strip()

        room_id = request.form.get("room_id", type=int) or None

        admission_date = request.form.get(
            "admission_date", ""
        )

        if not name:

            flash("Student name is required.")

        elif course not in get_options("course"):

            flash("Please select a valid course.")

        elif room_id and not db.execute(
            "SELECT id FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone():

            flash("Selected room does not exist.")

        else:

            db.execute("""
                INSERT INTO students
                (
                    name,
                    email,
                    phone,
                    course,
                    room_id,
                    admission_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                phone,
                course,
                room_id,
                admission_date
            ))

            db.commit()
            flash("Student added successfully!")

        db.close()

        return redirect(url_for("students"))

    student_rows = db.execute("""
        SELECT students.*, rooms.room_number
        FROM students

        LEFT JOIN rooms
        ON students.room_id = rooms.id

        ORDER BY students.id DESC
    """).fetchall()

    room_rows = db.execute("""
        SELECT *
        FROM rooms
        ORDER BY room_number
    """).fetchall()

    db.close()

    return render_template(
        "students.html",
        students=student_rows,
        rooms=room_rows,
        courses=get_options("course")
    )


@app.route("/students/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):

    db = get_db()

    db.execute(
        "DELETE FROM payments WHERE student_id = ?",
        (student_id,)
    )

    db.execute(
        "DELETE FROM complaints WHERE student_id = ?",
        (student_id,)
    )

    db.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    db.commit()
    db.close()

    flash("Student deleted successfully!")

    return redirect(url_for("students"))


# ======================================================
#                         ROOMS
# ======================================================

@app.route("/rooms", methods=["GET", "POST"])
def rooms():

    db = get_db()

    if request.method == "POST":

        room_number = request.form.get(
            "room_number", ""
        ).strip()

        room_type = request.form.get(
            "room_type", ""
        ).strip()

        capacity = request.form.get(
            "capacity", type=int
        )

        monthly_fee = request.form.get(
            "monthly_fee", type=float
        )

        if not room_number:

            flash("Room number is required.")

        elif room_type not in get_options("room_type"):

            flash("Please select a valid room type.")

        elif capacity is None or capacity < 1:

            flash("Room capacity must be at least 1.")

        elif monthly_fee is None or monthly_fee < 0:

            flash("Enter a valid monthly fee.")

        else:

            try:

                db.execute("""
                    INSERT INTO rooms
                    (
                        room_number,
                        room_type,
                        capacity,
                        monthly_fee
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    room_number,
                    room_type,
                    capacity,
                    monthly_fee
                ))

                db.commit()
                flash("Room added successfully!")

            except sqlite3.IntegrityError:

                flash("This room number already exists.")

        db.close()

        return redirect(url_for("rooms"))

    room_rows = db.execute("""
        SELECT rooms.*,

        (
            SELECT COUNT(*)
            FROM students
            WHERE students.room_id = rooms.id
        ) AS occupied

        FROM rooms
        ORDER BY rooms.room_number
    """).fetchall()

    db.close()

    return render_template(
        "rooms.html",
        rooms=room_rows,
        room_types=get_options("room_type")
    )


@app.route("/rooms/delete/<int:room_id>", methods=["POST"])
def delete_room(room_id):

    db = get_db()

    occupied = db.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE room_id = ?
    """, (room_id,)).fetchone()[0]

    if occupied > 0:

        flash("Cannot delete room. Students are assigned to it.")

    else:

        db.execute(
            "DELETE FROM rooms WHERE id = ?",
            (room_id,)
        )

        db.commit()
        flash("Room deleted successfully!")

    db.close()

    return redirect(url_for("rooms"))


# ======================================================
#                        PAYMENTS
# ======================================================

@app.route("/payments", methods=["GET", "POST"])
def payments():

    db = get_db()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id", type=int
        )

        amount = request.form.get(
            "amount", type=float
        )

        payment_date = request.form.get(
            "payment_date", ""
        )

        payment_method = request.form.get(
            "payment_method", ""
        ).strip()

        payment_statuses = get_options("payment_status")

        default_status = (
            "Paid" if "Paid" in payment_statuses
            else payment_statuses[0] if payment_statuses
            else ""
        )

        status = request.form.get(
            "status", default_status
        ).strip()

        student_exists = db.execute("""
            SELECT id
            FROM students
            WHERE id = ?
        """, (student_id,)).fetchone()

        if not student_exists:

            flash("Please select a valid student.")

        elif amount is None or amount <= 0:

            flash("Enter a valid payment amount.")

        elif payment_method not in get_options("payment_method"):

            flash("Please select a valid payment method.")

        elif status not in payment_statuses:

            flash("Please select a valid payment status.")

        else:

            db.execute("""
                INSERT INTO payments
                (
                    student_id,
                    amount,
                    payment_date,
                    payment_method,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                student_id,
                amount,
                payment_date,
                payment_method,
                status
            ))

            db.commit()
            flash("Payment added successfully!")

        db.close()

        return redirect(url_for("payments"))

    payment_rows = db.execute("""
        SELECT payments.*,
        students.name AS student_name

        FROM payments

        LEFT JOIN students
        ON payments.student_id = students.id

        ORDER BY payments.id DESC
    """).fetchall()

    student_rows = db.execute("""
        SELECT id, name
        FROM students
        ORDER BY name
    """).fetchall()

    db.close()

    return render_template(
        "payments.html",
        payments=payment_rows,
        students=student_rows,
        payment_methods=get_options("payment_method"),
        payment_statuses=get_options("payment_status")
    )


@app.route("/payments/delete/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):

    db = get_db()

    db.execute(
        "DELETE FROM payments WHERE id = ?",
        (payment_id,)
    )

    db.commit()
    db.close()

    flash("Payment deleted successfully!")

    return redirect(url_for("payments"))


# ======================================================
#                       COMPLAINTS
# ======================================================

@app.route("/complaints", methods=["GET", "POST"])
def complaints():

    db = get_db()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id", type=int
        )

        title = request.form.get(
            "title", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        complaint_date = request.form.get(
            "complaint_date", ""
        )

        complaint_statuses = get_options("complaint_status")

        default_status = (
            "Pending" if "Pending" in complaint_statuses
            else complaint_statuses[0] if complaint_statuses
            else ""
        )

        status = request.form.get(
            "status", default_status
        ).strip()

        student_exists = db.execute("""
            SELECT id
            FROM students
            WHERE id = ?
        """, (student_id,)).fetchone()

        if not student_exists:

            flash("Please select a valid student.")

        elif not title:

            flash("Complaint title is required.")

        elif status not in complaint_statuses:

            flash("Please select a valid complaint status.")

        else:

            db.execute("""
                INSERT INTO complaints
                (
                    student_id,
                    title,
                    description,
                    complaint_date,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                student_id,
                title,
                description,
                complaint_date,
                status
            ))

            db.commit()
            flash("Complaint submitted successfully!")

        db.close()

        return redirect(url_for("complaints"))

    complaint_rows = db.execute("""
        SELECT complaints.*,
        students.name AS student_name

        FROM complaints

        LEFT JOIN students
        ON complaints.student_id = students.id

        ORDER BY complaints.id DESC
    """).fetchall()

    student_rows = db.execute("""
        SELECT id, name
        FROM students
        ORDER BY name
    """).fetchall()

    db.close()

    return render_template(
        "complaints.html",
        complaints=complaint_rows,
        students=student_rows,
        complaint_statuses=get_options("complaint_status")
    )


@app.route(
    "/complaints/status/<int:complaint_id>",
    methods=["POST"]
)
def update_complaint_status(complaint_id):

    status = request.form.get(
        "status", ""
    ).strip()

    if status not in get_options("complaint_status"):

        flash("Invalid complaint status.")

    else:

        db = get_db()

        db.execute("""
            UPDATE complaints
            SET status = ?
            WHERE id = ?
        """, (status, complaint_id))

        db.commit()
        db.close()

        flash("Complaint status updated successfully!")

    return redirect(url_for("complaints"))


@app.route(
    "/complaints/delete/<int:complaint_id>",
    methods=["POST"]
)
def delete_complaint(complaint_id):

    db = get_db()

    db.execute(
        "DELETE FROM complaints WHERE id = ?",
        (complaint_id,)
    )

    db.commit()
    db.close()

    flash("Complaint deleted successfully!")

    return redirect(url_for("complaints"))


# ======================================================
#                          STAFF
# ======================================================

@app.route("/staff", methods=["GET", "POST"])
def staff():

    db = get_db()

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        role = request.form.get(
            "role", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        salary = request.form.get(
            "salary", type=float
        )

        if not name:

            flash("Staff name is required.")

        elif salary is not None and salary < 0:

            flash("Salary cannot be negative.")

        else:

            db.execute("""
                INSERT INTO staff
                (name, role, phone, salary)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                role,
                phone,
                salary
            ))

            db.commit()
            flash("Staff member added successfully!")

        db.close()

        return redirect(url_for("staff"))

    staff_rows = db.execute("""
        SELECT *
        FROM staff
        ORDER BY id DESC
    """).fetchall()

    db.close()

    return render_template(
        "staff.html",
        staff=staff_rows
    )


@app.route("/staff/delete/<int:staff_id>", methods=["POST"])
def delete_staff(staff_id):

    db = get_db()

    db.execute(
        "DELETE FROM staff WHERE id = ?",
        (staff_id,)
    )

    db.commit()
    db.close()

    flash("Staff member deleted successfully!")

    return redirect(url_for("staff"))


# ======================================================
#                         SETTINGS
# ======================================================

@app.route("/settings", methods=["GET", "POST"])
def settings():

    db = get_db()

    if request.method == "POST":

        hostel_name = request.form.get(
            "hostel_name", ""
        ).strip()

        hostel_address = request.form.get(
            "hostel_address", ""
        ).strip()

        contact_number = request.form.get(
            "contact_number", ""
        ).strip()

        db.execute("""
            UPDATE settings

            SET hostel_name = ?,
                hostel_address = ?,
                contact_number = ?

            WHERE id = 1
        """, (
            hostel_name,
            hostel_address,
            contact_number
        ))

        db.commit()
        db.close()

        flash("Hostel settings updated successfully!")

        return redirect(url_for("settings"))

    settings_row = db.execute("""
        SELECT *
        FROM settings
        WHERE id = 1
    """).fetchone()

    all_options = db.execute("""
        SELECT *
        FROM dropdown_options
        ORDER BY category, id
    """).fetchall()

    db.close()

    return render_template(
        "settings.html",
        settings=settings_row,
        all_options=all_options,
        category_names=CATEGORY_NAMES
    )


# ======================================================
#                  ADD DROPDOWN OPTION
# ======================================================

@app.route("/manage-options", methods=["POST"])
def manage_options():

    category = request.form.get(
        "category", ""
    ).strip()

    option = request.form.get(
        "option", ""
    ).strip()

    if category not in DEFAULT_OPTIONS:

        flash("Please select a valid category.")
        return redirect(url_for("settings"))

    if not option:

        flash("Please enter an option.")
        return redirect(url_for("settings"))

    if len(option) > 50:

        flash("Option must be 50 characters or fewer.")
        return redirect(url_for("settings"))

    db = get_db()

    try:

        db.execute("""
            INSERT INTO dropdown_options
            (category, option_value)
            VALUES (?, ?)
        """, (
            category,
            option
        ))

        db.commit()

        flash("New dropdown option added successfully!")

    except sqlite3.IntegrityError:

        flash("This option already exists.")

    finally:

        db.close()

    return redirect(url_for("settings"))


# ======================================================
#                 DELETE DROPDOWN OPTION
# ======================================================

@app.route(
    "/delete-option/<int:option_id>",
    methods=["POST"]
)
def delete_option(option_id):

    db = get_db()

    option = db.execute("""
        SELECT *
        FROM dropdown_options
        WHERE id = ?
    """, (option_id,)).fetchone()

    if not option:

        flash("Dropdown option not found.")

    else:

        category = option["category"]
        option_value = option["option_value"]

        total_options = db.execute("""
            SELECT COUNT(*)
            FROM dropdown_options
            WHERE category = ?
        """, (category,)).fetchone()[0]

        if total_options <= 1:

            flash("At least one option must remain in this category.")

        else:

            table_info = OPTION_USAGE_TABLES.get(category)

            is_used = False

            if table_info:

                table_name, column_name = table_info

                # Table and column names come only from the fixed mapping above
                usage_count = db.execute(
                    f"SELECT COUNT(*) FROM {table_name} "
                    f"WHERE {column_name} = ?",
                    (option_value,)
                ).fetchone()[0]

                is_used = usage_count > 0

            if is_used:

                flash(
                    "This option is already used in records "
                    "and cannot be deleted."
                )

            else:

                db.execute("""
                    DELETE FROM dropdown_options
                    WHERE id = ?
                """, (option_id,))

                db.commit()

                flash("Dropdown option deleted successfully!")

    db.close()

    return redirect(url_for("settings"))


# ======================================================
#                         404 PAGE
# ======================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template("404.html"), 404


# ======================================================
#                       RUN PROJECT
# ======================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)