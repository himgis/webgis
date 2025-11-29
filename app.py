import os
import tempfile
import zipfile
import shutil
import json
import random

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import geopandas as gpd

app = Flask(__name__)
CORS(app)

layers = {}   # Stores loaded layers


# ----------------------------------------------------
# HOME → Upload Page
# ----------------------------------------------------
@app.route('/')
def upload_page():
    return render_template('upload_page.html')


# ----------------------------------------------------
# Upload Shapefile (ZIP)
# ----------------------------------------------------
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith('.zip'):
        return jsonify({"error": "Please upload a ZIP containing the shapefile"}), 400

    temp_dir = tempfile.mkdtemp()

    try:
        zip_path = os.path.join(temp_dir, "uploaded.zip")

        # Save ZIP (bytes)
        file.save(zip_path)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_path = None
        for f in os.listdir(temp_dir):
            if f.lower().endswith(".shp"):
                shp_path = os.path.join(temp_dir, f)
                break

        if shp_path is None:
            return jsonify({"error": "No .shp file found inside ZIP"}), 400

        # Read shapefile
        gdf = gpd.read_file(shp_path)

        # Convert to GeoJSON dictionary
        geojson_data = json.loads(gdf.to_json())

        # Assign random color
        layer_color = "#" + ''.join(random.choices('0123456789ABCDEF', k=6))

        layer_name = os.path.basename(shp_path)

        # Store layer
        layers[layer_name] = {
            "geojson": geojson_data,
            "color": layer_color,
            "opacity": 0.9
        }

        return jsonify({"success": True, "layer_name": layer_name})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ----------------------------------------------------
# Map Page
# ----------------------------------------------------
@app.route('/map')
def map_page():
    return render_template('map.html')


# ----------------------------------------------------
# Fetch Layer List for Map
# ----------------------------------------------------
@app.route('/get_layers')
def get_layers():
    return jsonify(layers)


# ----------------------------------------------------
# Delete Layer
# ----------------------------------------------------
@app.route('/remove_layer', methods=['POST'])
def remove_layer():
    data = request.json
    name = data.get("layer_name")

    if name in layers:
        del layers[name]
        return jsonify({"success": True})

    return jsonify({"error": "Layer not found"}), 400


if __name__ == "__main__":
    app.run(debug=True)
