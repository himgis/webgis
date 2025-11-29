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
    <html><head><title>Upload Shapefile</title>
    <style>body{font-family:Arial;background:#f0f8ff;padding:50px;text-align:center}
    input,button{padding:15px;font-size:18px;margin:10px}</style></head>
    <body><h1>Upload District / Any Shapefile (ZIP)</h1>
    <input type="file" id="f" accept=".zip"><br><br>
    <button onclick="up()">Upload → Show on Map</button>
    <div id="msg" style="margin-top:20px;font-size:20px;font-weight:bold"></div><hr>
    <a href="/">← Open Map</a>
    <script>
    async function up(){let file=document.getElementById('f').files[0];
    if(!file)return alert("Select a ZIP");
    let fd=new FormData();fd.append('shpzip',file);
    document.getElementById('msg').innerText="Uploading…";
    let r=await fetch('/upload',{method:'POST',body:fd});
    let j=await r.json();
    document.getElementById('msg').innerHTML=
      r.ok ? "<span style='color:green'>SUCCESS! Layer: "+j.layer+"</span>"
           : "<span style='color:red'>Error: "+j.error+"</span>";
    }</script></body></html>
    '''

@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global
    try:
        file = request.files["shpzip"]
        zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(zip_path)

        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        shp = [f for f in os.listdir(extract_dir) if f.lower().endswith('.shp')][0]
        gdf = gpd.read_file(os.path.join(extract_dir, shp))
        gdf = gdf.to_crs(epsg=4326)

        name = os.path.splitext(shp)[0]
        color = random_color()

        layers[name] = {"geojson": gdf.__geo_interface__, "color": color}
        bounds_global = [[gdf.total_bounds[1], gdf.total_bounds[0]],
                         [gdf.total_bounds[3], gdf.total_bounds[2]]]

        # cleanup
        shutil.rmtree(extract_dir)
        os.remove(zip_path)

        return jsonify({"status": "success", "layer": name, "color": color})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/layers")
def get_layers():
    return jsonify({"layers": layers, "bounds": bounds_global})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
