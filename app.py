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
app.secret_key = "secret123"

# MongoDB connection
db = client.carpool
parents = db.parents
rides = db.rides
users = db.users

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

        users.insert_one({
            "name": name,
            "phone": phone,
            "password": password,
            "is_admin": False
        })
        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]

        user = users.find_one({"phone": phone, "password": password})
        if user:
            session["user"] = user["name"]
            session["phone"] = user["phone"]
            session["admin"] = user.get("is_admin", False)
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

    ride = {
        "parent": session["user"],
        "phone": session["phone"],
        "day": request.form["day"],
        "date": request.form["date"],
        "seats": request.form["seats"],
        "society": request.form["society"],
        "area": request.form["area"],
        "students": [
            {
                "name": request.form["student_name"],
                "section": request.form["section"]
            }
        ]
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

    all_rides = list(rides.find())
    return render_template(
        "rides.html",
        rides=all_rides,
        admin=session.get("admin", False)
    )

# =========================
# ADD STUDENT TO EXISTING RIDE
# =========================
@app.route("/add-student/<ride_id>", methods=["POST"])
def add_student(ride_id):
    student = {
        "name": request.form["student_name"],
        "section": request.form["section"]
    }

    rides.update_one(
        {"_id": ObjectId(ride_id)},
        {"$push": {"students": student}}
    )
    return redirect("/rides")

# =========================
# DELETE RIDE
# =========================
@app.route("/delete-ride/<ride_id>")
def delete_ride(ride_id):
    rides.delete_one({"_id": ObjectId(ride_id)})
    return redirect("/rides")

# =========================
# DELETE ALL (ADMIN ONLY)
# =========================
@app.route("/delete-all")
def delete_all():
    if not session.get("admin"):
        return "Unauthorized"
    rides.delete_many({})
    return redirect("/rides")

# =========================
# UPDATE RIDE (simple version)
# =========================
@app.route("/update-ride/<ride_id>", methods=["GET", "POST"])
def update_ride(ride_id):
    ride = rides.find_one({"_id": ObjectId(ride_id)})

    if request.method == "POST":
        rides.update_one(
            {"_id": ObjectId(ride_id)},
            {"$set": {
                "day": request.form["day"],
                "date": request.form["date"],
                "seats": request.form["seats"],
                "society": request.form["society"],
                "area": request.form["area"]
            }}
        )
        return redirect("/rides")

    return render_template("update_ride.html", ride=ride)

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
