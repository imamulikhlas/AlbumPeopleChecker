import os
import json
import uuid
from datetime import datetime
from typing import Tuple, List, Dict, Any
from flask import Flask, request, jsonify, render_template, send_from_directory
import face_recognition
import mysql.connector
from werkzeug.utils import secure_filename
from functools import lru_cache
import logging
from mysql.connector import pooling

# Konfigurasi
UPLOAD_DIR = "Python/static/images_upload"
SEARCH_DIR = "Python/static/images_search"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 1920  # Maximum width/height in pixels

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Konfigurasi koneksi pool database
dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "password",
    "database": "face_recognition",
    "pool_name": "mypool",
    "pool_size": 5
}

try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**dbconfig)
except Exception as e:
    logger.error(f"Failed to create connection pool: {str(e)}")
    raise

app = Flask(__name__)

# Inisialisasi direktori
for directory in [UPLOAD_DIR, SEARCH_DIR]:
    os.makedirs(directory, exist_ok=True)

def allowed_file(filename: str) -> bool:
    """Validasi ekstensi file yang diizinkan."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file) -> Tuple[bool, str]:
    """Validasi file gambar."""
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No filename provided"
    
    if not allowed_file(file.filename):
        return False, f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024}MB"
    
    return True, ""

def get_db_connection():
    """Get connection from connection pool."""
    try:
        return connection_pool.get_connection()
    except Exception as e:
        logger.error(f"Error getting database connection: {str(e)}")
        raise

@lru_cache(maxsize=100)
def load_faces_from_db() -> Tuple[List, List, List]:
    """Load face encodings from database with caching."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, encoding, file_name FROM known_faces")
        faces = cursor.fetchall()
        
        known_encodings = []
        known_names = []
        file_names = []
        
        for name, encoding, file_name in faces:
            known_encodings.append(json.loads(encoding))
            known_names.append(name)
            file_names.append(file_name)
            
        return known_encodings, known_names, file_names
    
    except Exception as e:
        logger.error(f"Error loading faces from database: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def save_face_to_db(name: str, encoding: Any, file_name: str) -> None:
    """Save face encoding to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tambahkan timestamp
        created_at = datetime.now()
        
        cursor.execute(
            "INSERT INTO known_faces (name, encoding, file_name, created_at) VALUES (%s, %s, %s, %s)", 
            (name, json.dumps(encoding.tolist()), file_name, created_at)
        )
        conn.commit()
        
        # Invalidate cache after new face is added
        load_faces_from_db.cache_clear()
        
    except Exception as e:
        logger.error(f"Error saving face to database: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

@app.route("/add_known_face", methods=["POST"])
def add_known_face():
    """Add new face endpoint with improved validation and error handling."""
    try:
        if 'name' not in request.form:
            return jsonify({"error": "Name is required"}), 400
        
        name = request.form['name'].strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        
        file = request.files.get('file')
        is_valid, error_message = validate_image_file(file)
        if not is_valid:
            return jsonify({"error": error_message}), 400

        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        new_file_name = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, new_file_name)
        
        # Save file
        file.save(file_path)
        
        try:
            # Verify face encoding
            image = face_recognition.load_image_file(file_path)
            encodings = face_recognition.face_encodings(image)
            
            if not encodings:
                os.remove(file_path)
                return jsonify({"error": "No face detected in the uploaded image"}), 400
            
            if len(encodings) > 1:
                os.remove(file_path)
                return jsonify({"error": "Multiple faces detected. Please upload an image with only one face"}), 400
            
            # Save to database
            save_face_to_db(name, encodings[0], new_file_name)
            
            return jsonify({
                "message": f"{name} added successfully!",
                "file_name": new_file_name
            }), 200
            
        except Exception as e:
            # Clean up file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
            
    except Exception as e:
        logger.error(f"Error in add_known_face: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/find_face", methods=["POST"])
def find_face():
    """Find face endpoint with improved validation and performance."""
    try:
        file = request.files.get('file')
        is_valid, error_message = validate_image_file(file)
        if not is_valid:
            return jsonify({"error": error_message}), 400

        # Save file with secure name
        filename = secure_filename(file.filename)
        file_path = os.path.join(SEARCH_DIR, filename)
        file.save(file_path)

        try:
            # Process image
            uploaded_image = face_recognition.load_image_file(file_path)
            uploaded_encodings = face_recognition.face_encodings(uploaded_image)

            if not uploaded_encodings:
                return jsonify({"error": "No face detected in the uploaded image"}), 400

            if len(uploaded_encodings) > 1:
                return jsonify({"error": "Multiple faces detected. Please upload an image with only one face"}), 400

            # Get face matches
            known_encodings, known_names, file_names = load_faces_from_db()
            results = face_recognition.compare_faces(known_encodings, uploaded_encodings[0], tolerance=0.6)
            face_distances = face_recognition.face_distance(known_encodings, uploaded_encodings[0])

            matches = [
                {
                    "name": known_names[i],
                    "similarity_score": round(1 - distance, 2),
                    "file_name": file_names[i]
                }
                for i, (match, distance) in enumerate(zip(results, face_distances))
                if match
            ]

            return jsonify({
                "match": bool(matches),
                "matches": matches or [],
                "message": "No matching face found" if not matches else None
            })

        finally:
            # Clean up temporary search file
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        logger.error(f"Error in find_face: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/search")
def search():
    return render_template("search.html")

# @app.route('/static/images_upload/<path:filename>')
# def serve_upload(filename):
#     """Serve uploaded images with security checks."""
#     if '..' in filename or filename.startswith('/'):
#         return jsonify({"error": "Invalid filename"}), 400
#     return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=False)  # Set debug=False in production