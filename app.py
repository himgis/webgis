import os
import tempfile
import zipfile
import shutil
import random
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import geopandas as gpd

app = Flask(__name__)
CORS(app)

layers = {}  # Stores all layers: name → {geojson, color, opacity}


# ---------------- Home / Map ----------------
@app.route("/")
def index():
    return render_template("map.html")


# ---------------- Upload Page ----------------
@app.route("/upload_page")
def upload_page():
    return render_template("upload_page.html")


# ---------------- Upload API (Multiple ZIPs) ----------------
@app.route("/upload", methods=["POST"])
def upload_shapefiles():
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

            # Find the first .shp file
            shp_file = next((os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(".shp")), None)
            if not shp_file:
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
            print("ERROR processing file:", file.filename, e)
            failed.append(file.filename)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return jsonify({"uploaded": uploaded, "failed": failed})


# ---------------- Return All Layers ----------------
@app.route("/layers")
def get_layers():
    bounds = None
    if layers:
        first_layer = next(iter(layers.values()))
        gdf = gpd.GeoDataFrame.from_features(first_layer["geojson"]["features"], crs="EPSG:4326")
        b = gdf.total_bounds
        bounds = [[b[1], b[0]], [b[3], b[2]]]  # Leaflet: [[southWest], [northEast]]

    return jsonify({"layers": layers, "bounds": bounds})


# ---------------- Run Server ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
