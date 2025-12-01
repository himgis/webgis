import os
import tempfile
import zipfile
import shutil
import random
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import geopandas as gpd

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"   # change this
CORS(app)

ADMIN_USER = "admin"
ADMIN_PASS = "1234"

layers = {}  # Stores all layers: name → {geojson, color, opacity}


# ---------------- Login Page ----------------
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


# ---------------- Login API ----------------
@app.route("/login", methods=["POST"])
def login_api():
    data = request.get_json()

    if data["username"] == ADMIN_USER and data["password"] == ADMIN_PASS:
        session["admin"] = True
        return jsonify({"message": "Logged in"})
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return jsonify({"message": "Logged out"})


# ---------------- Home / Map ----------------
@app.route("/")
def index():
    is_admin = session.get("admin", False)
    return render_template("map.html", is_admin=is_admin)


# ---------------- Upload Page ----------------
@app.route("/upload_page")
def upload_page():
    if not session.get("admin"):
        return "Unauthorized", 403

    return render_template("upload_page.html")


# ---------------- Upload Shapefiles (Admin Only) ----------------
@app.route("/upload", methods=["POST"])
def upload_shapefiles():

    if not session.get("admin"):
        return jsonify({"error": "Only admin can upload!"}), 403

    if "files" not in request.files:
        return jsonify({"error": "No files received!"}), 400

    files = request.files.getlist("files")
    uploaded = []
    failed = []

    for file in files:
        if not file.filename.lower().endswith(".zip"):
            failed.append(file.filename)
            continue

        temp_dir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)

            shp_file = None
            for root, dirs, files2 in os.walk(temp_dir):
                for f in files2:
                    if f.lower().endswith(".shp"):
                        shp_file = os.path.join(root, f)
                        break

            if shp_file is None:
                failed.append(file.filename)
                continue

            gdf = gpd.read_file(shp_file)
            geojson_dict = gdf.to_crs("EPSG:4326").__geo_interface__

            layer_name = os.path.splitext(file.filename)[0]
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

            layers[layer_name] = {
                "geojson": geojson_dict,
                "color": color,
                "opacity": 0.7
            }

            uploaded.append(layer_name)

        except Exception as e:
            print("ERROR:", file.filename, e)
            failed.append(file.filename)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return jsonify({"uploaded": uploaded, "failed": failed})


# ---------------- Delete Layer (Admin Only) ----------------
@app.route("/delete/<layer_name>", methods=["DELETE"])
def delete_layer(layer_name):

    if not session.get("admin"):
        return jsonify({"error": "Only admin can delete!"}), 403

    if layer_name in layers:
        layers.pop(layer_name)
        return jsonify({"message": "Deleted"})
    else:
        return jsonify({"error": "Layer not found"}), 404


# ---------------- Send Layers to Frontend ----------------
@app.route("/layers")
def get_layers():
    is_admin = session.get("admin", False)

    final_bounds = None
    if layers:
        all_bounds = []
        for lyr in layers.values():
            gdf = gpd.GeoDataFrame.from_features(lyr["geojson"]["features"], crs="EPSG:4326")
            b = gdf.total_bounds
            all_bounds.append(b)

        minx = min(b[0] for b in all_bounds)
        miny = min(b[1] for b in all_bounds)
        maxx = max(b[2] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)

        final_bounds = [[miny, minx], [maxy, maxx]]

    return jsonify({
        "is_admin": is_admin,
        "layers": layers,
        "bounds": final_bounds
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
