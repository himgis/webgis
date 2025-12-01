import os
import tempfile
import zipfile
import shutil
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import geopandas as gpd

app = Flask(__name__)
CORS(app)

# Store all layers in memory
layers = {}   # {layer_name : { "geojson": {}, "color": "", "opacity": 1 }}

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
        return jsonify({"error": "No ZIP files received!"}), 400

    uploaded_files = request.files.getlist("files")

    uploaded = []
    failed = []

    for file in uploaded_files:

        # Accept ONLY zip files
        if not file.filename.lower().endswith(".zip"):
            failed.append(file.filename)
            continue

        # Create temp folder
        temp_dir = tempfile.mkdtemp()

        try:
            # Save uploaded ZIP
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)

            # Extract ZIP
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)

            # Find .shp file inside ZIP
            shp_file = None
            for f in os.listdir(temp_dir):
                if f.endswith(".shp"):
                    shp_file = os.path.join(temp_dir, f)
                    break

            if not shp_file:
                failed.append(file.filename)
                continue

            # Read using GeoPandas
            gdf = gpd.read_file(shp_file)

            # Convert to GeoJSON
            geojson_data = gdf.to_json()

            # Layer name → filename without extension
            layer_name = os.path.splitext(file.filename)[0]

            # Save layer
            layers[layer_name] = {
                "geojson": geojson_data,
                "color": "#FF0000",
                "opacity": 0.7,
            }

            uploaded.append(layer_name)

        except Exception as e:
            print("ERROR:", e)
            failed.append(file.filename)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return jsonify({"uploaded": uploaded, "failed": failed})


# ---------- API: GET ALL LAYERS ----------
@app.route("/layers")
def get_layers():
    return jsonify(layers)


# ---------- REQUIRED FOR RENDER.COM ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
