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

# Store layers in memory
layers = {}  # layer_name → {geojson, color, opacity}


# ---------- HOME PAGE (MAP) ----------
@app.route("/")
def index():
    return render_template("map.html")


# ---------- UPLOAD PAGE ----------
@app.route("/upload_page")
def upload_page():
    return render_template("upload_page.html")


# ---------- MULTIPLE ZIP UPLOAD API ----------
@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files received!"}), 400

    uploaded_files = request.files.getlist("files")
    uploaded = []
    failed = []

    for file in uploaded_files:
        if not file.filename.lower().endswith(".zip"):
            failed.append(file.filename)
            continue

        temp_dir = tempfile.mkdtemp()

        try:
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)

            # Extract ZIP
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)

            # Find .shp file inside ZIP
            shp_file = None
            for f in os.listdir(temp_dir):
                if f.lower().endswith(".shp"):
                    shp_file = os.path.join(temp_dir, f)
                    break

            if not shp_file:
                failed.append(file.filename)
                continue

            # Read shapefile
            gdf = gpd.read_file(shp_file)

            # Convert to WGS84 + GeoJSON dict
            geojson_dict = gdf.to_crs("EPSG:4326").__geo_interface__

            layer_name = os.path.splitext(file.filename)[0]

            # Random color
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

            layers[layer_name] = {
                "geojson": geojson_dict,
                "color": color,
                "opacity": 0.7
            }

            uploaded.append(layer_name)

        except Exception as e:
            print("ERROR:", e)
            failed.append(file.filename)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return jsonify({"uploaded": uploaded, "failed": failed})


# ---------- SEND ALL LAYERS TO MAP ----------
@app.route("/layers")
def get_layers():
    # Optionally compute bounds for first layer
    bounds = None
    if layers:
        first_layer = next(iter(layers.values()))
        gdf = gpd.GeoDataFrame.from_features(first_layer["geojson"]["features"], crs="EPSG:4326")
        b = gdf.total_bounds  # minx, miny, maxx, maxy
        bounds = [[b[1], b[0]], [b[3], b[2]]]  # Leaflet [southWest, northEast]

    return jsonify({"layers": layers, "bounds": bounds})


# ---------- RUN SERVER ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
