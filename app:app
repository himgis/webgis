import os
import json
import zipfile
import tempfile
import shutil
import random
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import geopandas as gpd

app = Flask(__name__)
CORS(app)

layers = {}   # Stored layers: name -> {geojson, color, opacity}


@app.route("/")
def home():
    return render_template("map.html")


@app.route("/upload_page")
def upload_page():
    return render_template("upload_page.html")


# -------------------------------
# UPLOAD SHAPEFILE (ZIP)
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not file.filename.lower().endswith(".zip"):
        return jsonify({"error": "Upload a .zip containing shapefile"}), 400

    # Create temp directory
    temp_dir = tempfile.mkdtemp()

    try:
        zip_path = os.path.join(temp_dir, "uploaded.zip")
        file.save(zip_path)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)

        # Find .shp file
        shp_file = None
        for f in os.listdir(temp_dir):
            if f.lower().endswith(".shp"):
                shp_file = os.path.join(temp_dir, f)
                break

        if not shp_file:
            return jsonify({"error": "No .shp file found inside ZIP"}), 400

        # Read shapefile
        gdf = gpd.read_file(shp_file)

        # Convert to GeoJSON dict (not string)
        geojson = json.loads(gdf.to_json())

        # Generate random color
        color = "#" + ''.join(random.choices("0123456789ABCDEF", k=6))

        name = os.path.basename(shp_file)

        layers[name] = {
            "geojson": geojson,
            "color": color,
            "opacity": 0.8
        }

        return jsonify({"success": True, "layer_name": name})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# -------------------------------
# SEND LAYERS TO MAP
# -------------------------------
@app.route("/layers")
def get_layers():
    try:
        # Compute combined bounds
        all_bounds = None

        for info in layers.values():
            gdf = gpd.GeoDataFrame.from_features(info["geojson"]["features"])
            if not gdf.empty:
                b = gdf.total_bounds  # minx, miny, maxx, maxy
                if all_bounds is None:
                    all_bounds = b
                else:
                    all_bounds = [
                        min(all_bounds[0], b[0]),
                        min(all_bounds[1], b[1]),
                        max(all_bounds[2], b[2]),
                        max(all_bounds[3], b[3])
                    ]

        return jsonify({
            "layers": layers,
            "bounds": all_bounds
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------
# IMPORTANT: Render.com PORT FIX
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Running on port {port}...")
    app.run(host="0.0.0.0", port=port)
