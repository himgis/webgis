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
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

@app.route("/")
def home():
    return render_template("map.html")

@app.route("/upload-page")
def upload_page():
    return '''
    <html><head><title>Upload Shapefile ZIP</title>
    <style>body{font-family:Arial;background:#e8f5e9;padding:60px;text-align:center}
    h1{color:#2e7d32}input,button{padding:15px 30px;font-size:18px;margin:10px;border-radius:10px}
    button{background:#43a047;color:white;border:none;cursor:pointer}
    </style></head>
    <body>
    <h1>Upload District / Taluka / Village Boundary</h1>
    <input type="file" id="f" accept=".zip"><br><br>
    <button onclick="upload()">Upload to Map</button>
    <div id="msg" style="margin:30px;font-size:22px;font-weight:bold"></div>
    <hr><a href="/" style="font-size:20px;color:#2e7d32">Open Live Map</a>
    <script>
    async function upload(){
        const file = document.getElementById('f').files[0];
        if(!file){alert("Select a ZIP file");return;}
        const fd = new FormData(); fd.append('shpzip', file);
        document.getElementById('msg').innerHTML = "Uploading...";
        const r = await fetch('/upload', {method:'POST', body:fd});
        const j = await r.json();
        document.getElementById('msg').innerHTML = 
            r.ok ? "<span style='color:green'>SUCCESS! Added: <b>"+j.layer+"</b></span>"
                 : "<span style='color:red'>ERROR: "+j.error+"</span>";
    }
    </script>
    </body></html>
    '''

@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global
    try:
        # THIS IS THE ONLY SAFE WAY — NEVER use .get()
        if 'shpzip' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['shpzip']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save & process
        zip_path = os.path.join(UPLOAD_FOLDER, file.filename.replace(" ", "_"))
        file.save(zip_path)

        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        shp_files = [f for f in os.listdir(extract_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(extract_dir); os.remove(zip_path)
            return jsonify({"error": "No .shp file found in ZIP"}), 400

        gdf = gpd.read_file(os.path.join(extract_dir, shp_files[0]))
        gdf = gdf.to_crs(epsg=4326)

        layer_name = os.path.splitext(shp_files[0])[0]
        color = random_color()

        layers[layer_name] = {"geojson": gdf.__geo_interface__, "color": color}
        bounds_global = [[gdf.total_bounds[1], gdf.total_bounds[0]],
                         [gdf.total_bounds[3], gdf.total_bounds[2]]]

        shutil.rmtree(extract_dir)
        os.remove(zip_path)

        return jsonify({"status": "success", "layer": layer_name, "color": color})

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/layers")
def get_layers():
    return jsonify({"layers": layers, "bounds": bounds_global})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
