@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return "No files uploaded", 400

    uploaded_files = request.files.getlist("files")

    for file in uploaded_files:
        if file.filename == "":
            continue

        filename = file.filename

        # Save ZIP file
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, filename)
        file.save(zip_path)

        # Extract ZIP
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Detect .shp file
        shp_file = None
        for f in os.listdir(extract_dir):
            if f.endswith(".shp"):
                shp_file = os.path.join(extract_dir, f)
                break

        if shp_file is None:
            shutil.rmtree(temp_dir)
            continue

        # Read shapefile
        gdf = gpd.read_file(shp_file)

        # Convert to GeoJSON
        geojson = gdf.to_crs("EPSG:4326").__geo_interface__

        # Assign random color
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

        # Save in global dictionary
        layer_name = os.path.splitext(filename)[0]
        layers[layer_name] = {
            "geojson": geojson,
            "color": color,
            "opacity": 0.7
        }

        shutil.rmtree(temp_dir)

    return '''
        <h2>Upload Successful!</h2>
        <a href="/map">Go to Map</a>
    '''
