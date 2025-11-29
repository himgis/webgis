import os
import zipfile
import tempfile
import shutil
import random
import geopandas as gpd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Global storage
layers = {}
bounds_global = None
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# ———————— Home ————————
@app.route("/")
def home():
    return render_template("map.html")

# ———————— Upload Page ————————
@app.route("/upload-page")
def upload_page():
    return '''
    <html>
    <head><title>Upload Shapefile ZIP</title>
    <style>
        body{font-family:Arial;background:#e8f5e9;padding:50px;text-align:center}
        h1{color:#2e7d32} input,button{padding:15px 30px;font-size:18px;margin:10px;border-radius:8px}
        button{background:#43a047;color:white;border:none;cursor:pointer}
        button:hover{background:#388e3c}
    </style>
    </head>
    <body>
        <h1>Upload District / Taluka / Village (ZIP)</h1>
        <input type="file" id="f" accept=".zip"><br><br>
        <button onclick="upload()">Upload & Show on Map</button>
        <div id="msg" style="margin:30px;font-size:22px;font-weight:bold"></div>
        <hr><a href="/" style="font-size:20px;color:#2e7d32">Open Live Map →</a>
        <script>
        async function upload(){
            const file = document.getElementById('f').files[0];
            if(!file){alert("Please select a ZIP file");return;}
            const fd = new FormData();
            fd.append('shpzip', file);
            document.getElementById('msg').innerHTML = "Uploading...";
            try{
                const r = await fetch('/upload', {method:'POST', body:fd});
                const j = await r.json();
                document.getElementById('msg').innerHTML = 
                    r.ok ? "<span style='color:green'>SUCCESS! Layer added: <b>"+j.layer+"</b></span>"
                         : "<span style='color:red'>ERROR: "+j.error+"</span>";
            }catch(e){
                document.getElementById('msg').innerHTML = "<span style='color:red'>Network error</span>";
            }
        }
        </script>
    </body>
    </html>
    '''

# ———————— UPLOAD ROUTE (THIS IS THE FINAL FIX) ————————
@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global
    try:
        if 'shpzip' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['shpzip']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # THE ONLY BULLETPROOF WAY — read as bytes first
        zip_bytes = file.read()
        if len(zip_bytes) == 0:
            return jsonify({"error": "Empty file"}), 400

        # Create temp folder and write bytes safely
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        # Extract
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        # Find .shp
        shp_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(temp_dir)
            return jsonify({"error": "No .shp file found in ZIP"}), 400

        # Read and convert
        gdf = gpd.read_file(os.path.join(temp_dir, shp_files[0]))
        gdf = gdf.to_crs(epsg=4326)

        layer_name = os.path.splitext(shp_files[0])[0]
        color = random_color()

        layers[layer_name] = {
            "geojson": gdf.__geo_interface__,
            "color": color
        }

        # Auto-zoom
        b = gdf.total_bounds
        bounds_global = [[b[1], b[0]], [b[3], b[2]]]

        # Cleanup
        shutil.rmtree(temp_dir)

        return jsonify({"status": "success", "layer": layer_name, "color": color})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ———————— Layers API ————————
@app.route("/layers")
def get_layers():
    return jsonify({"layers": layers, "bounds": bounds_global})

# ———————— Run ————————
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
