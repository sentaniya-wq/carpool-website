from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_wtf.csrf import CSRFProtect
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os
import certifi

# =========================
# MongoDB connection
# =========================
MONGO_URL = "mongodb+srv://carpool-db-user:Welcome1$@carpool-cluster.hacthov.mongodb.net/?appName=carpool-cluster"
client = MongoClient(MONGO_URL, tls=True, tlsCAFile=certifi.where())
db = client.carpool
users = db.users
rides = db.rides
parents = db.parents

ADMIN_PHONE = "999999999"

# =========================
# Flask App
# =========================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# CSRF Protection
csrf = CSRFProtect(app)

# Session config
app.config.update(
    SESSION_COOKIE_SAMESITE="None" if os.environ.get("FLASK_ENV") == "production" else "Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
)

# =========================
# ABOUT
# =========================
@app.route("/about")
def about():
    return render_template("about.html")

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return redirect(url_for('login') if "user" not in session else url_for('dashboard'))

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        password = request.form.get("password")

        if not name or not phone or not password:
            flash("All fields are required", "error")
            return redirect(url_for("register"))

        if users.find_one({"phone": phone}):
            flash("User already exists", "error")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        users.insert_one({"name": name, "phone": phone, "password": hashed_pw})
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")
        student_name = request.form.get("student")

        if not phone or not password:
            flash("Phone and password are required", "error")
            return redirect(url_for("login"))

        user = users.find_one({"phone": phone})
        if user and check_password_hash(user["password"], password):
            session["user"] = user["name"]
            session["phone"] = phone
            session["student"] = student_name
            session["admin"] = phone == ADMIN_PHONE

            # Store students of this parent for dropdown
            session["students"] = list(rides.find({"phone": phone}, {"students": 1}))
            flash(f"Welcome {user['name']}", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    # Handle adding student
    if request.method == "POST":
        student_name = request.form.get("student_name")
        section = request.form.get("section")
        if student_name and section:
            rides.insert_one({
                "day": "", "date": "", "parent": session["user"], "phone": session["phone"],
                "society": "", "area": "", "total_seats": 0, "available_seats": 0,
                "students": [{"name": student_name, "section": section, "parent_phone": session["phone"]}]
            })
            flash(f"Student {student_name} added", "success")
            return redirect(url_for("dashboard"))

    # Fetch students
    students_cursor = rides.find({"phone": session["phone"]}, {"students": 1})
    students = []
    for ride in students_cursor:
        for s in ride.get("students", []):
            if s not in students:
                students.append(s)

    return render_template("dashboard.html", name=session["user"], students=students)

# =========================
# ADD RIDE
# =========================
@app.route("/add-ride", methods=["POST"])
def add_ride():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        total_seats = int(request.form.get("seats", 0))
    except ValueError:
        flash("Invalid number of seats", "error")
        return redirect(url_for("dashboard"))

    ride = {
        "day": request.form.get("day"),
        "date": request.form.get("date"),
        "parent": session["user"],
        "phone": session["phone"],
        "society": request.form.get("society"),
        "area": request.form.get("area"),
        "total_seats": total_seats,
        "available_seats": total_seats,
        "students": [{
            "name": request.form.get("student_name"),
            "section": request.form.get("section"),
            "parent_phone": session["phone"]
        }]
    }
    rides.insert_one(ride)
    flash("Ride added successfully", "success")
    return redirect(url_for("view_rides"))

# =========================
# VIEW RIDES
# =========================
@app.route("/rides")
def view_rides():
    if "user" not in session:
        return redirect(url_for("login"))
    all_rides = list(rides.find().sort("date", 1))
    return render_template("rides.html", rides=all_rides, admin=session.get("admin"))

# =========================
# MY RIDES
# =========================
@app.route("/my-rides")
def my_rides():
    if "phone" not in session:
        return redirect(url_for("login"))

    phone = session["phone"]
    student = session.get("student")

    created = list(rides.find({"phone": phone}))
    joined = []

    if student:
        for ride in rides.find({"students.parent_phone": phone}):
            for s in ride.get("students", []):
                if s.get("parent_phone") == phone and s.get("name", "").lower() == student.lower():
                    joined.append(ride)
                    break

    return render_template("my-rides.html", created=created, joined=joined, selected_student=student)

# =========================
# ADD STUDENT TO EXISTING RIDE
# =========================
@app.route("/add-student/<ride_id>", methods=["POST"])
def add_student(ride_id):
    if "phone" not in session:
        return redirect(url_for("login"))

    ride = rides.find_one({"_id": ObjectId(ride_id)})
    if not ride:
        flash("Ride not found", "error")
        return redirect(url_for("view_rides"))

    if ride["available_seats"] <= 0:
        flash("Ride is full", "error")
        return redirect(url_for("view_rides"))

    student = {
        "name": request.form.get("student_name"),
        "section": request.form.get("section"),
        "parent_phone": session["phone"]
    }
    rides.update_one({"_id": ObjectId(ride_id)}, {"$push": {"students": student}, "$inc": {"available_seats": -1}})
    flash(f"Student {student['name']} added to ride", "success")
    return redirect(url_for("view_rides"))

# =========================
# DELETE RIDE
# =========================
@app.route("/delete-ride/<ride_id>", methods=["POST"])
def delete_ride(ride_id):
    if "phone" not in session:
        return redirect(url_for("login"))

    ride = rides.find_one({"_id": ObjectId(ride_id)})
    if not ride:
        flash("Ride not found", "error")
        return redirect(url_for("view_rides"))

    if ride["phone"] != session["phone"]:
        flash("Not authorized", "error")
        return redirect(url_for("view_rides"))

    rides.delete_one({"_id": ObjectId(ride_id)})
    flash("Ride deleted successfully", "info")
    return redirect(url_for("view_rides"))

# =========================
# DELETE ALL RIDES (ADMIN)
# =========================
@app.route("/delete-all", methods=["POST"])
def delete_all():
    if not session.get("admin"):
        flash("Admins only", "error")
        return redirect(url_for("view_rides"))

    rides.delete_many({})
    flash("All rides deleted", "info")
    return redirect(url_for("view_rides"))

# =========================
# UPDATE RIDE
# =========================
@app.route("/update-ride/<ride_id>", methods=["GET", "POST"])
def update_ride(ride_id):
    if "phone" not in session:
        return redirect(url_for("login"))

    ride = rides.find_one({"_id": ObjectId(ride_id)})
    if not ride:
        flash("Ride not found", "error")
        return redirect(url_for("view_rides"))

    if ride["phone"] != session["phone"]:
        flash("Not authorized", "error")
        return redirect(url_for("view_rides"))

    if request.method == "POST":
        rides.update_one(
            {"_id": ObjectId(ride_id)},
            {"$set": {
                "day": request.form.get("day"),
                "date": request.form.get("date"),
                "society": request.form.get("society"),
                "area": request.form.get("area")
            }}
        )
        flash("Ride updated successfully", "success")
        return redirect(url_for("view_rides"))

    return render_template("update-ride.html", ride=ride)

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)