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
layers = {}   # layer_name → { geojson, color, opacity }


@app.route("/")
def index():
    return render_template("map.html")


@app.route("/upload_page")
def upload_page():
    return render_template("upload_page.html")


# ================================
# MULTIPLE SHAPEFILE UPLOAD API
# ================================
@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files received"}), 400

    uploaded_files = request.files.getlist("files")

    uploaded = []
    failed = []

    for file in uploaded_files:

        try:
            filename = file.filename
            if filename.strip() == "":
                continue

            # Create temp directory
            temp_dir = tempfile.mkdtemp()

            zip_path = os.path.join(temp_dir, filename)
            file.save(zip_path)

            # Extract ZIP
            extract_dir = os.path.join(temp_dir, "extract")
            os.makedirs(extract_dir, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(extract_dir)
            except:
                failed.append(filename)
                shutil.rmtree(temp_dir)
                continue

            # Find .shp file
            shp_path = None
            for f in os.listdir(extract_dir):
                if f.lower().endswith(".shp"):
                    shp_path = os.path.join(extract_dir, f)
                    break

            if shp_path is None:
                failed.append(filename)
                shutil.rmtree(temp_dir)
                continue

            # Read shapefile
            try:
                gdf = gpd.read_file(shp_path)
            except:
                failed.append(filename)
                shutil.rmtree(temp_dir)
                continue

            # Convert to WGS84 + GeoJSON
            gdf = gdf.to_crs("EPSG:4326")
            geojson = gdf.__geo_interface__

            # Generate a random color
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

            layer_name = os.path.splitext(filename)[0]

            layers[layer_name] = {
                "geojson": geojson,
                "color": color,
                "opacity": 0.7
            }

            uploaded.append(layer_name)

            shutil.rmtree(temp_dir)

        except:
            failed.append(file.filename)

    return jsonify({
        "uploaded": uploaded,
        "failed": failed
    }), 200


# ================================
# SEND ALL LAYERS TO MAP
# ================================
@app.route("/layers")
def get_layers():
    # compute bounds if only 1 layer
    bounds = None

    if len(layers) == 1:
        for name, info in layers.items():
            gdf = gpd.GeoDataFrame.from_features(info["geojson"]["features"], crs="EPSG:4326")
            bounds = gdf.total_bounds.tolist()  # [minx, miny, maxx, maxy]

    return jsonify({
        "layers": layers,
        "bounds": bounds
    })


# ================================
# Run locally (ignored on Render)
# ================================
if __name__ == "__main__":
    app.run(debug=True)
