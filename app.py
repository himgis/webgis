import os
import zipfile
import tempfile
import shutil
import random
import geopandas as gpd
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

# ==================== Flask Setup ====================
app = Flask(__name__)
CORS(app)

# Global storage
layers = {}           # name → {geojson, color}
bounds_global = None
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==================== Helper Functions ====================
def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


# ==================== Routes ====================
@app.route("/")
def home():
    return render_template("map.html")


# Simple & beautiful upload page
@app.route("/upload-page")
def upload_page():
    return '''
    <html>
    <head>
        <title>Upload Shapefile ZIP</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body{font-family:Arial,sans-serif;background:#f4f6f9;padding:40px;text-align:center}
            h1{color:#2c3e50}
            input,button{padding:15px 20px;font-size:18px;margin:15px}
            button{background:#3498db;color:white;border:none;border-radius:8px;cursor:pointer}
            button:hover{background:#2980b9}
            a{color:#3498db;font-size:18px}
        </style>
    </head>
    <body>
        <h1>Multi-Layer WebGIS</h1>
        <p><strong>Upload a Shapefile (.zip)</strong></p>
        <input type="file" id="file" accept=".zip"><br><br>
        <button onclick="upload()">Upload & Show on Map</button>
        <div id="msg" style="margin-top:25px;font-size:19px;font-weight:bold"></div>
        <hr>
        <a href="/">Open Full Map</a>
        <script>
        async function upload(){
            const f = document.getElementById('file').files[0];
            if (!f) return alert("Please select a ZIP file");
            const fd = new FormData();
            fd.append('shpzip', f);
            document.getElementById('msg').innerHTML = "Uploading...";
            try {
                const r = await fetch('/upload', {method:'POST', body:fd});
                const j = await r.json();
                document.getElementById('msg').innerHTML = 
                    r.ok ? "<span style='color:green'>Success! Layer added: <b>"+j.layer+"</b></span>"
                         : "<span style='color:red'>Error: "+j.error+"</span>";
            } catch(e) {
                document.getElementById('msg').innerHTML = "<span style='color:red'>Upload failed</span>";
            }
        }
        </script>
    </body>
    </html>
    '''


@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global
    try:
        file = request.files.get("shpzip")
        if not file:
            return jsonify({"error": "No file received"}), 400

        # Save uploaded ZIP
        temp_zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(temp_zip_path)

        # Extract
        extract_folder = tempfile.mkdtemp()
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)

        # Find .shp file
        shp_files = [f for f in os.listdir(extract_folder) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(extract_folder)
            os.remove(temp_zip_path)
            return jsonify({"error": "No .shp file found in ZIP"}), 400

        shp_path = os.path.join(extract_folder, shp_files[0])
        gdf = gpd.read_file(shp_path)
        gdf = gdf.to_crs(epsg=4326)
        geojson = gdf.__geo_interface__

        layer_name = os.path.splitext(shp_files[0])[0]
        color = random_color()

        layers[layer_name] = {
            "geojson": geojson,
            "color": color,
            "opacity": 0.6
        }

        # Auto-zoom to first layer
        bounds = gdf.total_bounds
        bounds_global = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]

        # Cleanup
        shutil.rmtree(extract_folder)
        os.remove(temp_zip_path)

        return jsonify({
            "status": "success",
            "layer": layer_name,
            "color": color
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/layers")
def get_layers():
    return jsonify({
        "layers": layers,
        "bounds": bounds_global
    })


# ==================== Run App (Render + Local) ====================
if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
