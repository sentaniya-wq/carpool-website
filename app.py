from flask import Flask, render_template, request, redirect, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import certifi

# =========================
# MongoDB connection
# =========================
MONGO_URL = "mongodb+srv://carpool-db-user:Welcome1$@carpool-cluster.hacthov.mongodb.net/?appName=carpool-cluster"

client = MongoClient(
    MONGO_URL,
    tls=True,
    tlsCAFile=certifi.where()
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# ADD THIS
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

# MongoDB connection
db = client.carpool
parents = db.parents
rides = db.rides
users = db.users

ADMIN_PHONE = "999999999"

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
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        password = request.form["password"]

        if users.find_one({"phone": phone}):
            return "User already exists"

        users.insert_one({
            "name": name,
            "phone": phone,
            "password": password
        })
        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]

        user = users.find_one({"phone": phone, "password": password})
        if user:
            session["user"] = user["name"]
            session["phone"] = phone
            session["admin"] = (phone == ADMIN_PHONE)
            return redirect("/dashboard")

    return render_template("login.html")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["user"])

# =========================
# ADD RIDE
# =========================
@app.route("/add-ride", methods=["POST"])
def add_ride():
    if "user" not in session:
        return redirect("/login")

    total = int(request.form["seats"])

    ride = {
        "day": request.form["day"],
        "date": request.form["date"],
        "parent": session["user"],
        "phone": session["phone"],
        "society": request.form["society"],
        "area": request.form["area"],
        "total_seats": total,
        "available_seats": total,
        "students": [{
            "name": request.form["student_name"],
            "section": request.form["section"],
            "phone": session["phone"]
        }]
    }

    rides.insert_one(ride)
    return redirect("/rides")

# =========================
# VIEW RIDES
# =========================
@app.route("/rides")
def view_rides():
    if "user" not in session:
        return redirect("/login")

    all_rides = list(rides.find().sort("date", 1))
    return render_template("rides.html", rides=all_rides, admin=session.get("admin"))

# =========================
# MY RIDES
# =========================
@app.route("/my-rides")
def my_rides():
    if "phone" not in session:
        return redirect("/login")

    phone = session["phone"]

    created = list(rides.find({"phone": phone}))
    joined = list(rides.find({"students.phone": phone}))

    return render_template("my-rides.html", created=created, joined=joined)

# =========================
# ADD STUDENT TO EXISTING RIDE
# =========================
@app.route("/add-student/<ride_id>", methods=["POST"])
def add_student(ride_id):
    if "phone" not in session:
        return redirect("/login")

    ride = rides.find_one({"_id": ObjectId(ride_id)})

    if ride["available_seats"] <= 0:
        return "Ride is full"

    student = {
        "name": request.form["student_name"],
        "section": request.form["section"],
        "phone": session["phone"]
    }

    rides.update_one(
        {"_id": ObjectId(ride_id)},
        {
            "$push": {"students": student},
            "$inc": {"available_seats": -1}
        }
    )
    return redirect("/rides")

# =========================
# DELETE RIDE
# =========================
@app.route("/delete-ride/<ride_id>", methods=["POST"])
def delete_ride(ride_id):
    if "phone" not in session:
        return redirect("/login")

    ride = rides.find_one({"_id": ObjectId(ride_id)})

    if ride["phone"] != session["phone"]:
        return "Not authorized"

    rides.delete_one({"_id": ObjectId(ride_id)})
    return redirect("/rides")

# =========================
# DELETE ALL (ADMIN ONLY)
# =========================
@app.route("/delete-all")
def delete_all():
    if not session.get("admin"):
        return "Admins only"

    rides.delete_many({})
    return redirect("/rides")

# =========================
# UPDATE RIDE
# =========================
@app.route("/update-ride/<ride_id>", methods=["GET", "POST"])
def update_ride(ride_id):
    if "phone" not in session:
        return redirect("/login")

    ride = rides.find_one({"_id": ObjectId(ride_id)})

    if ride["phone"] != session["phone"]:
        return "Not authorized"

    if request.method == "POST":
        rides.update_one(
            {"_id": ObjectId(ride_id)},
            {"$set": {
                "day": request.form["day"],
                "date": request.form["date"],
                "society": request.form["society"],
                "area": request.form["area"]
            }}
        )
        return redirect("/rides")

    return render_template("update-ride.html", ride=ride)

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
