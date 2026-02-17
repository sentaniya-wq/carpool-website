from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
import certifi

MONGO_URL = "mongodb+srv://carpool-db-user:Welcome1$@carpool-cluster.hacthov.mongodb.net/?appName=carpool-cluster"

client = MongoClient(
    MONGO_URL,
    tls=True,
    tlsCAFile=certifi.where()
)

app = Flask(__name__)
app.secret_key = "carpoolsecret"

# MongoDB connection
db = client.carpool
parents = db.parents
rides = db.rides

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        parents.insert_one({
            "name": request.form["name"],
            "phone": request.form["phone"],
            "area": request.form["area"],
            "password": request.form["password"]
        })
        return redirect("/login")
    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = parents.find_one({
            "phone": request.form["phone"],
            "password": request.form["password"]
        })
        if user:
            session["phone"] = user["phone"]
            session["name"] = user["name"]
            return redirect("/dashboard")
    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", name=session["name"])

# ---------------- ADD RIDE ----------------
@app.route("/add-ride", methods=["POST"])
def add_ride():
    rides.insert_one({
        "name": session["name"],
        "phone": session["phone"],
        "day": request.form["day"],
        "seats": request.form["seats"],
        "area": request.form["area"],
        "available": True
    })
    return redirect("/dashboard")

# ---------------- VIEW RIDES ----------------
@app.route("/rides")
def view_rides():
    all_rides = list(rides.find({"available": True}))
    return render_template("rides.html", rides=all_rides)

app.run(debug=True)
