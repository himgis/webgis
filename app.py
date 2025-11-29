import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import geopandas as gpd
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import zipfile
import tempfile
import shutil
import requests
import random

app = Flask(__name__)
CORS(app)

layers = {}   # layer_name: {geojson, color, opacity}
bounds_global = None

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

@app.route("/")
def home():
    return render_template("map.html")

@app.route("/upload", methods=["POST"])
def upload_shapefile():
    global bounds_global

    try:
        file = request.files.get("shpzip")
        if not file:
            return jsonify({"error": "No file received"}), 400

        temp_zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(temp_zip_path)

        extract_folder = tempfile.mkdtemp()
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)

        shp_files = [f for f in os.listdir(extract_folder) if f.lower().endswith('.shp')]
        if not shp_files:
            shutil.rmtree(extract_folder)
            return jsonify({"error": "No .shp file found"}), 400

        shp_path = os.path.join(extract_folder, shp_files[0])

        gdf = gpd.read_file(shp_path)
        gdf = gdf.to_crs(epsg=4326)

        geojson = gdf.__geo_interface__

        layer_name = os.path.splitext(shp_files[0])[0]

        color = random_color()
        opacity = round(random.uniform(0.3, 0.8), 2)

        layers[layer_name] = {
            "geojson": geojson,
            "color": color,
            "opacity": opacity
        }

        bounds = gdf.total_bounds
        bounds_global = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]

        shutil.rmtree(extract_folder)

        return jsonify({
            "status": "success",
            "layer": layer_name,
            "color": color,
            "opacity": opacity
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/layers")
def get_layers():
    return jsonify({
        "layers": layers,
        "bounds": bounds_global
    })

def run_flask():
    print("Server running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)

# ------------ Tkinter UI --------------

def select_shapefile_zip():
    file_path = filedialog.askopenfilename(
        title="Select Shapefile ZIP",
        filetypes=[("ZIP files", "*.zip")]
    )

    if not file_path:
        return

    try:
        with open(file_path, "rb") as f:
            files = {"shpzip": f}
            response = requests.post("http://127.0.0.1:5000/upload", files=files)

        if response.status_code == 200:
            info = response.json()
            messagebox.showinfo(
                "Uploaded",
                f"Layer: {info['layer']}\nColor: {info['color']}\nOpacity: {info['opacity']}"
            )
        else:
            messagebox.showerror("Upload Failed", response.json().get("error"))

    except Exception as e:
        messagebox.showerror("Error", str(e))

def open_map():
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")

def start_flask():
    threading.Thread(target=run_flask, daemon=True).start()

# Tk window
root = tk.Tk()
root.title("Shapefile GIS Tool")
root.geometry("420x260")

tk.Label(root, text="Multi Layer Web GIS", font=("Arial", 14)).pack(pady=10)
tk.Button(root, text="Upload Shapefile ZIP", command=select_shapefile_zip, height=2).pack(pady=10)
tk.Button(root, text="Open Web Map", command=open_map, height=2).pack(pady=10)

start_flask()
root.mainloop()
