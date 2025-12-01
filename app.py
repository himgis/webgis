import os
import zipfile
import tempfile
import shutil
import random
import geopandas as gpd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

layers = {}
bounds_global = None


def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


# ---------------- HOME PAGE -----------------

@app.route("/")
def home():
    return render_template("map.html")


# --------------- UPLOAD PAGE ----------------

@app.route("/upload_page")
def upload_page():
    return render_template("upload_page.html")


# --------------- SHAPEFILE UPLOAD API ---------------

@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global

    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file received"}), 400

        file = request.files['file']
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Read ZIP bytes safely
        zip_bytes = file.read()
        temp_dir = tempfile.mkdtemp()

        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        # Extract files
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        # Find .shp file
        shp_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(".shp")]
        if not shp_files:
            shutil.rmtree(temp_dir)
            return jsonify({"error": "ZIP does not contain a .shp file"}), 400

        shp_path = os.path.join(temp_dir, shp_files[0])

        # Read shapefile → GeoJSON
        gdf = gpd.read_file(shp_path)
        gdf = gdf.to_crs(4326)

        name = os.path.splitext(shp_files[0])[0]
        color = random_color()

        layers[name] = {
            "geojson": gdf.__geo_interface__,
            "color": color
        }

        b = gdf.total_bounds
        bounds_global = [[b[1], b[0]], [b[3], b[2]]]

        shutil.rmtree(temp_dir)
        return jsonify({"status": "success", "layer": name, "color": color})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------- SEND LAYERS TO MAP --------------

@app.route("/layers")
def get_layers():
    return jsonify({"layers": layers, "bounds": bounds_global})


# ---------------- RUN FOR RENDER --------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
