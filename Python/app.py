import os
import json
import uuid
from flask import Flask, request, jsonify , render_template,send_from_directory
import face_recognition
import mysql.connector
from werkzeug.utils import secure_filename

UPLOAD_DIR = "Python/static/images_upload"
SEARCH_DIR = "Python/static/images_search"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEARCH_DIR, exist_ok=True)

app = Flask(__name__)

# Koneksi ke database MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # Ganti dengan user database Anda
        password="password",  # Ganti dengan password Anda
        database="face_recognition"  # Ganti dengan nama database Anda
    )

# Menyimpan encoding wajah baru dan file ke database
def save_face_to_db(name, encoding, file_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO known_faces (name, encoding, file_name) VALUES (%s, %s, %s)", 
                   (name, json.dumps(encoding.tolist()), file_name))
    conn.commit()
    cursor.close()
    conn.close()

# Memuat semua encoding dari database
def load_faces_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, encoding, file_name FROM known_faces")
    faces = cursor.fetchall()
    cursor.close()
    conn.close()
    known_encodings = []
    known_names = []
    file_names = []
    for name, encoding, file_name in faces:
        known_encodings.append(json.loads(encoding))
        known_names.append(name)
        file_names.append(file_name)
    return known_encodings, known_names, file_names

# Endpoint untuk menambahkan wajah baru
@app.route("/add_known_face", methods=["POST"])
def add_known_face():
    if 'file' not in request.files or 'name' not in request.form:
        return jsonify({"error": "File and name are required"}), 400
    file = request.files['file']
    name = request.form['name']

    # Generate nama file baru
    new_file_name = f"{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(UPLOAD_DIR, new_file_name)
    file.save(file_path)

    # Verifikasi encoding wajah
    image = face_recognition.load_image_file(file_path)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        os.remove(file_path)  # Hapus file jika tidak ada wajah
        return jsonify({"error": "No face detected in the uploaded image"}), 400

    # Simpan encoding pertama ke database
    save_face_to_db(name, encodings[0], new_file_name)
    return jsonify({"message": f"{name} added successfully!", "file_name": new_file_name}), 200

# Endpoint untuk mencari wajah
@app.route("/find_face", methods=["POST"])
def find_face():
    if 'file' not in request.files:
        return jsonify({"error": "File is required"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join(SEARCH_DIR, filename)
    file.save(file_path)

    # Muat gambar upload
    uploaded_image = face_recognition.load_image_file(file_path)
    uploaded_encodings = face_recognition.face_encodings(uploaded_image)

    # Cek apakah ada wajah dalam gambar
    if not uploaded_encodings:
        os.remove(file_path)  # Hapus file jika tidak ada wajah
        return jsonify({"error": "No face detected in the uploaded image"}), 400

    # Cek apakah lebih dari satu wajah terdeteksi
    if len(uploaded_encodings) > 1:
        os.remove(file_path)  # Hapus file jika lebih dari satu wajah
        return jsonify({"error": "Multiple faces detected. Please upload an image with only one face"}), 400

    uploaded_encoding = uploaded_encodings[0]

    # Muat wajah yang dikenal dari database
    known_encodings, known_names, file_names = load_faces_from_db()
    results = face_recognition.compare_faces(known_encodings, uploaded_encoding, tolerance=0.6)
    face_distances = face_recognition.face_distance(known_encodings, uploaded_encoding)

    matches = []
    for i, match in enumerate(results):
        if match:
            matches.append({
                "name": known_names[i],
                "similarity_score": round(1 - face_distances[i], 2),
                "file_name": file_names[i]  # Kembalikan file gambar terkait
            })

    if matches:
        return jsonify({
            "match": True,
            "matches": matches
        })
    else:
        return jsonify({
            "match": False,
            "message": "No matching face found"
        })
    
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/search")
def search():
    return render_template("search.html")

# Public Image Assets
# @app.route('/static/<path:filename>') 
# def send_file(filename): 
#     return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True)
