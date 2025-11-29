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

@app.route("/")
def home():
    return render_template("map.html")

@app.route("/upload-page")
def upload_page():
    return '''
    <html><head><title>Upload Shapefile</title>
    <style>body{font-family:Arial;background:#fffde7;padding:60px;text-align:center}
    h1{color:#f57f17}input,button{padding:18px 35px;font-size:20px;margin:15px;border-radius:12px}
    button{background:#ff9800;color:white;border:none;cursor:pointer;font-weight:bold}
    </style></head>
    <body>
    <h1>Upload Any Shapefile (ZIP)</h1>
    <input type="file" id="f" accept=".zip"><br><br>
    <button onclick="upload()">UPLOAD NOW</button>
    <div id="msg" style="margin:40px;font-size:24px;font-weight:bold"></div>
    <hr><a href="/" style="font-size:22px;color:#ff9800">Open Map</a>
    <script>
    async function upload(){
        const file = document.getElementById('f').files[0];
        if(!file){alert("Select ZIP file");return;}
        const fd = new FormData(); fd.append('file', file);
        document.getElementById('msg').innerHTML = "Uploading...";
        const r = await fetch('/upload', {method:'POST', body:fd});
        const j = await r.json();
        document.getElementById('msg').innerHTML = 
            r.ok ? "<span style='color:green'>SUCCESS! Layer: <b>"+j.layer+"</b></span>"
                 : "<span style='color:red'>ERROR: "+j.error+"</span>";
    }
    </script>
    </body></html>
    '''

@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global
    try:
        if 'file' not in request.files:                     # ← CHANGED FROM 'shpzip' to 'file'
            return jsonify({"error": "No file"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # READ AS BYTES – THIS IS THE ONLY WAY THAT NEVER FAILS
        zip_bytes = file.stream.read()
        
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "temp.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(temp_dir)
            return jsonify({"error": "No .shp in ZIP"}), 400

        gdf = gpd.read_file(os.path.join(temp_dir, shp_files[0]))
        gdf = gdf.to_crs(epsg=4326)

        name = os.path.splitext(shp_files[0])[0]
        color = random_color()

        layers[name] = {"geojson": gdf.__geo_interface__, "color": color}
        b = gdf.total_bounds
        bounds_global = [[b[1], b[0]], [b[3], b[2]]]

        shutil.rmtree(temp_dir)
        return jsonify({"status": "success", "layer": name, "color": color})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/layers")
def get_layers():
    return jsonify({"layers": layers, "bounds": bounds_global})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
