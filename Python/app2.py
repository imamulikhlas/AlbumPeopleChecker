import os
import json
import uuid
from datetime import datetime
from math import ceil
from typing import Tuple, List, Dict, Any
from flask import Flask, request, jsonify, render_template, send_from_directory
import face_recognition
import mysql.connector
from werkzeug.utils import secure_filename
from functools import lru_cache
import logging
from mysql.connector import pooling
import cv2
import numpy as np
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# Konfigurasi
UPLOAD_DIR = os.getenv("DB_HOST")
SEARCH_DIR = os.getenv("SEARCH_DIR")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 1920  # Maximum width/height in pixels

# Konfigurasi deteksi wajah yang dioptimalkan
DETECTION_METHOD = 'hog'  # 'hog' lebih cepat, 'cnn' lebih akurat jika ada GPU
TOLERANCE = 0.45  # Nilai default 0.6, lebih kecil = lebih ketat
NUM_JITTERS = 3  # Meningkatkan akurasi encoding wajah
UPSAMPLE_TIMES = 1  # Membantu mendeteksi wajah kecil atau tidak jelas

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Konfigurasi koneksi pool database
dbconfig = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "pool_name": os.getenv("DB_POOL_NAME"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", 5))  # Default 5 jika tidak diset
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

def preprocess_image(image_path: str) -> np.ndarray:
    """Preprocess gambar untuk meningkatkan kualitas deteksi."""
    # Baca gambar
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not load image")
    
    # Konversi ke RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Resize jika terlalu besar
    height, width = image.shape[:2]
    if max(height, width) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(height, width)
        image = cv2.resize(image, None, fx=scale, fy=scale)
    
    # Perbaiki kontras
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    lab = cv2.merge([l,a,b])
    image = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    
    return image

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
        
        created_at = datetime.now()
        
        cursor.execute(
            "INSERT INTO known_faces (name, encoding, file_name, created_at) VALUES (%s, %s, %s, %s)", 
            (name, json.dumps(encoding.tolist()), file_name, created_at)
        )
        conn.commit()
        
        load_faces_from_db.cache_clear()
        
    except Exception as e:
        logger.error(f"Error saving face to database: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def get_face_encodings(image: np.ndarray) -> List:
    """Get face encodings with multiple angle detection."""
    encodings = []
    
    # Coba deteksi normal
    face_locations = face_recognition.face_locations(
        image, 
        number_of_times_to_upsample=UPSAMPLE_TIMES,
        model=DETECTION_METHOD
    )
    if face_locations:
        encodings.extend(face_recognition.face_encodings(
            image, 
            face_locations,
            num_jitters=NUM_JITTERS
        ))
    
    # Jika tidak ada wajah terdeteksi, coba dengan rotasi
    if not encodings:
        for angle in [90, 180, 270]:
            rotated = np.rot90(image, k=angle//90)
            face_locations = face_recognition.face_locations(
                rotated,
                number_of_times_to_upsample=UPSAMPLE_TIMES,
                model=DETECTION_METHOD
            )
            if face_locations:
                new_encodings = face_recognition.face_encodings(
                    rotated,
                    face_locations,
                    num_jitters=NUM_JITTERS
                )
                encodings.extend(new_encodings)
    
    return encodings

# Constants
ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE"))  # Jumlah item per halaman

def prepare_paginated_response(matches: List[Dict[str, Any]], page: int = 1) -> Dict[str, Any]:
    """Mempersiapkan response dengan pagination."""
    total_items = len(matches)
    total_pages = ceil(total_items / ITEMS_PER_PAGE)
    
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    current_items = matches[start_idx:end_idx]
    
    return {
        "match": bool(matches),
        "matches": current_items,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "items_per_page": ITEMS_PER_PAGE,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@app.route("/add_known_face", methods=["POST"])
def add_known_face():
    """Add new face endpoint with improved detection."""
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

        file_ext = file.filename.rsplit('.', 1)[1].lower()
        new_file_name = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, new_file_name)
        
        file.save(file_path)
        
        try:
            # Preprocess dan deteksi wajah
            processed_image = preprocess_image(file_path)
            encodings = get_face_encodings(processed_image)
            
            if not encodings:
                os.remove(file_path)
                return jsonify({"error": "No face detected in the uploaded image"}), 400
            
            saved_faces = []
            for i, encoding in enumerate(encodings):
                face_name = f"{name}" if len(encodings) == 1 else f"{name}_{i+1}"
                save_face_to_db(face_name, encoding, new_file_name)
                saved_faces.append(face_name)
            
            return jsonify({
                "message": f"Successfully added {len(saved_faces)} faces!",
                "details": {
                    "file_name": new_file_name,
                    "faces_detected": len(saved_faces),
                    "saved_names": saved_faces
                }
            }), 200
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Error processing image: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Error in add_known_face: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/find_face", methods=["POST"])
def find_face():
    """Find face endpoint with improved matching."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "File is required"}), 400

        file = request.files['file']
        page = int(request.form.get('page', 1))
        
        is_valid, error_message = validate_image_file(file)
        if not is_valid:
            return jsonify({"error": error_message}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(SEARCH_DIR, filename)
        file.save(file_path)

        try:
            # Preprocess dan deteksi wajah
            processed_image = preprocess_image(file_path)
            uploaded_encodings = get_face_encodings(processed_image)

            if not uploaded_encodings:
                return jsonify({"error": "No face detected in the uploaded image"}), 400

            if len(uploaded_encodings) > 1:
                return jsonify({"error": "Multiple faces detected. Please upload an image with only one face"}), 400

            # Get face matches with improved comparison
            known_encodings, known_names, file_names = load_faces_from_db()
            matches = []
            
            for i, known_encoding in enumerate(known_encodings):
                # Hitung jarak wajah
                face_distance = face_recognition.face_distance(
                    [np.array(known_encoding)],
                    uploaded_encodings[0]
                )[0]
                
                # Konversi ke similarity score
                similarity_score = 1 - face_distance
                
                if similarity_score >= (1 - TOLERANCE):
                    matches.append({
                        "name": known_names[i],
                        "similarity_score": round(float(similarity_score), 3),
                        "file_name": file_names[i],
                        "confidence_level": get_confidence_level(similarity_score)
                    })
            
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            if not matches:
                return jsonify({
                    "match": False,
                    "message": "No faces found with sufficient similarity score",
                    "matches": [],
                    "pagination": {
                        "current_page": 1,
                        "total_pages": 0,
                        "total_items": 0,
                        "items_per_page": ITEMS_PER_PAGE,
                        "has_next": False,
                        "has_prev": False
                    }
                })
            
            response_data = prepare_paginated_response(matches, page)
            return jsonify(response_data)

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        logger.error(f"Error in find_face: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def get_confidence_level(similarity_score: float) -> str:
    """Kategorisasi level kepercayaan berdasarkan similarity score."""
    if similarity_score >= 0.85:
        return "Very High"
    elif similarity_score >= 0.75:
        return "High"
    elif similarity_score >= 0.65:
        return "Medium"
    else:
        return "Low"

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/search")
def search():
    return render_template("search.html")

if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production