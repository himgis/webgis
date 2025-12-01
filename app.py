import os
import zipfile
import tempfile
import shutil
import random
import string
import geopandas as gpd
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "MY_SECRET_KEY_123"   # Change for security

CORS(app)

UPLOAD_FOLDER = "layers"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
#  ADMIN LOGIN CREDENTIALS
# -----------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "1234"


# -----------------------------
#   AUTH CHECK DECORATOR
# -----------------------------
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# -----------------------------
#  LOGIN PAGE
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# -----------------------------
#  LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------------
#  ADMIN DASHBOARD
# -----------------------------
@app.route("/admin")
@admin_required
def admin():
    layers = [f.replace(".geojson", "") for f in os.listdir(UPLOAD_FOLDER)]
    return render_template("admin.html", layers=layers)


# -----------------------------
#  HANDLE SHAPEFILE UPLOAD
# -----------------------------
@app.route("/upload", methods=["POST"])
@admin_required
def upload_file():
    file = request.files.get("file")

    if not file:
        return "No file uploaded", 400

    if not file.filename.endswith(".zip"):
        return "Upload a zipped shapefile", 400

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, file.filename)
    file.save(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_file = None
    for f in os.listdir(temp_dir):
        if f.endswith(".shp"):
            shp_file = os.path.join(temp_dir, f)
            break

    if not shp_file:
        shutil.rmtree(temp_dir)
        return "Shapefile not found in ZIP", 400

    # Read SHP → GeoJSON
    gdf = gpd.read_file(shp_file)
    name = os.path.splitext(os.path.basename(shp_file))[0]

    # Save GeoJSON
    output_path = os.path.join(UPLOAD_FOLDER, name + ".geojson")
    gdf.to_file(output_path, driver="GeoJSON")

    shutil.rmtree(temp_dir)
    return redirect("/admin")


# -----------------------------
#  DELETE LAYER 
# -----------------------------
@app.route("/delete/<name>", methods=["GET"])
@admin_required
def delete_layer(name):
    path = os.path.join(UPLOAD_FOLDER, name + ".geojson")
    if os.path.exists(path):
        os.remove(path)
    return redirect("/admin")


# -----------------------------
#  LIST LAYERS FOR MAP.HTML
# -----------------------------
@app.route("/layers")
def list_layers():
    layers = {}
    bounds = None

    for f in os.listdir(UPLOAD_FOLDER):
        if f.endswith(".geojson"):
            path = os.path.join(UPLOAD_FOLDER, f)
            gdf = gpd.read_file(path)
            name = f.replace(".geojson", "")

            color = "#" + "".join(random.choice("0123456789ABCDEF") for _ in range(6))

            layers[name] = {
                "geojson": gdf.__geo_interface__,
                "color": color
            }

            if bounds is None:
                bounds = gdf.total_bounds

    return jsonify({"layers": layers, "bounds": bounds})


# -----------------------------
#  PUBLIC MAP PAGE
# -----------------------------
@app.route("/")
def map_page():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(debug=True)
