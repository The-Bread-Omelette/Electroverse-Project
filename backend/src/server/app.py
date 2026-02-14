from flask import Flask, request, Response, jsonify
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import json
import hashlib

app = Flask(__name__)

# 1. Connect to Mongo
client = MongoClient("mongodb://localhost:27017/")
db = client.video_storage_db

# TTL index for auto-deletion after 7 days
db.fs.files.create_index("uploadDate", expireAfterSeconds=604800)
fs = gridfs.GridFS(db)

# Users collection for authentication
users_collection = db.users

# 2. Upload limit (500MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# ============================================
# HELPER FUNCTIONS
# ============================================

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Check if username and password match"""
    if not username or not password:
        return False
        
    user = users_collection.find_one({"username": username})
    
    if not user:
        return False
    
    hashed_input = hash_password(password)
    return user['password'] == hashed_input

def get_auth_from_request():
    """Extract username and password from request headers"""
    username = request.headers.get('X-Username')
    password = request.headers.get('X-Password')
    return username, password

def cleanup_orphaned_chunks():
    """Deletes data chunks that no longer have a parent file document due to TTL."""
    valid_ids = db.fs.files.distinct("_id")
    result = db.fs.chunks.delete_many({"files_id": {"$nin": valid_ids}})
    print(f"Cleanup: Removed {result.deleted_count} orphaned chunks.")

# ============================================
# USER MANAGEMENT ROUTES
# ============================================

def register():
    """Register a new user"""
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'viewer')  # viewer, uploader, admin
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Check if user already exists
    if users_collection.find_one({"username": username}):
        return jsonify({"error": "User already exists"}), 409
    
    # Create new user
    user = {
        "username": username,
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.utcnow()
    }
    
    users_collection.insert_one(user)
    
    return jsonify({
        "message": "User registered successfully",
        "username": username,
        "role": role
    }), 201

@app.route('/login', methods=['POST'])
def login():
    """Verify user credentials"""
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    if verify_user(username, password):
        user = users_collection.find_one({"username": username})
        return jsonify({
            "message": "Login successful",
            "username": username,
            "role": user['role']
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# ============================================
# VIDEO ROUTES (WITH AUTH)
# ============================================

@app.route('/')
def home():
    return "Encrypted Video Server is Running"

def upload():
    # 1. Authenticate user
    username, password = get_auth_from_request()
    
    if not username or not password:
        return jsonify({"error": "Missing authentication headers (X-Username, X-Password)"}), 401
    
    if not verify_user(username, password):
        return jsonify({"error": "Authentication failed - Invalid credentials"}), 401
    
    # 2. Check if user has upload permission
    user = users_collection.find_one({"username": username})
    if user['role'] not in ['uploader', 'admin']:
        return jsonify({"error": "No upload permission"}), 403
    
    # 3. Process upload
    if 'video' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['video']
    camera_id = request.form.get('camera_id', 'CAM_67')
    
    file_id = fs.put(
        file, 
        filename=file.filename, 
        content_type='application/octet-stream',
        metadata={
            "camera_id": camera_id,
            "plate_numbers": [],
            "is_encrypted": True,
            "container_format": "WattLagGyi",
            "uploaded_by": username
        }
    )
    
    return jsonify({
        "video_id": str(file_id),
        "status": "stored_encrypted",
        "uploaded_by": username
    }), 201

@app.route('/video/<video_id>')
def stream_video(video_id):
    # Authenticate user
    username, password = get_auth_from_request()
    
    if not username or not password:
        return jsonify({"error": "Missing authentication headers (X-Username, X-Password)"}), 401
    
    if not verify_user(username, password):
        return jsonify({"error": "Authentication failed"}), 401
    
    try:
        video_file = fs.get(ObjectId(video_id))
        
        def generate():
            for chunk in video_file:
                yield chunk

        return Response(generate(), mimetype='application/octet-stream')
    except Exception:
        return jsonify({"error": "Video not found"}), 404

def update_plate(video_id):
    # Authenticate user
    username, password = get_auth_from_request()
    
    if not username or not password:
        return jsonify({"error": "Missing authentication headers (X-Username, X-Password)"}), 401
    
    if not verify_user(username, password):
        return jsonify({"error": "Authentication failed"}), 401
    
    # Check permission
    user = users_collection.find_one({"username": username})
    if user['role'] not in ['uploader', 'admin']:
        return jsonify({"error": "No permission to update metadata"}), 403
    
    data = request.get_json()
    plate_numbers = data.get('plate_numbers')

    if not plate_numbers:
        return jsonify({"error": "No plate number provided"}), 400

    result = db.fs.files.update_one(
        {"_id": ObjectId(video_id)},
        {"$push": {"metadata.plate_numbers": plate_numbers}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Video not found"}), 404

    return jsonify({"message": "Plate added to metadata"}), 200

@app.route('/search')
def search_videos():
    # Authenticate user
    username, password = get_auth_from_request()
    
    if not username or not password:
        return jsonify({"error": "Missing authentication headers (X-Username, X-Password)"}), 401
    
    if not verify_user(username, password):
        return jsonify({"error": "Authentication failed"}), 401
    
    plate = request.args.get('plate')
    date_str = request.args.get('date')
    camera_id = request.args.get('camera_id')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    query = {}

    if plate:
        query["metadata.plate_numbers"] = plate
    
    if camera_id:
        query["metadata.camera_id"] = camera_id

    if date_str:
        try:
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            if start_time_str and end_time_str:
                t_start = datetime.strptime(start_time_str, '%H:%M:%S').time()
                t_end = datetime.strptime(end_time_str, '%H:%M:%S').time()
                
                ist_start = datetime.combine(base_date, t_start)
                ist_end = datetime.combine(base_date, t_end)
            else:
                ist_start = base_date
                ist_end = ist_start + timedelta(days=1)

            utc_start = ist_start - timedelta(hours=5, minutes=30)
            utc_end = ist_end - timedelta(hours=5, minutes=30)
            
            query["uploadDate"] = {"$gte": utc_start, "$lt": utc_end}

        except ValueError:
            return jsonify({"error": "Invalid format. Use Date: YYYY-MM-DD, Time: HH:MM:SS"}), 400

    cursor = db.fs.files.find(query)
    results = []
    
    for video in cursor:        
        utc_time = video['uploadDate']
        ist_time = utc_time + timedelta(hours=5, minutes=30)

        results.append({
            "video_id": str(video['_id']),
            "filename": video['filename'],
            "camera_id": video.get('metadata', {}).get('camera_id'),
            "upload_date_ist": ist_time.strftime('%Y-%m-%d %H:%M:%S'),
            "plates_found": video.get('metadata', {}).get('plate_numbers', []),
            "uploaded_by": video.get('metadata', {}).get('uploaded_by')
        })

    if not results:
        return jsonify({"message": "No results found"}), 404

    return jsonify(results), 200

# ============================================
# ADMIN ROUTES
# ============================================

def list_users():
    """List all users (admin only)"""
    username, password = get_auth_from_request()
    
    # Better error message
    if not username or not password:
        return jsonify({
            "error": "Missing authentication headers",
            "required_headers": ["X-Username", "X-Password"]
        }), 401
    
    if not verify_user(username, password):
        return jsonify({"error": "Authentication failed - Invalid credentials"}), 401
    
    user = users_collection.find_one({"username": username})
    if user['role'] != 'admin':
        return jsonify({"error": "Admin access required. Your role: " + user['role']}), 403
    
    users = list(users_collection.find({}, {"password": 0}))
    
    for u in users:
        u['_id'] = str(u['_id'])
    
    return jsonify(users), 200

if __name__ == '__main__':
    cleanup_orphaned_chunks()
    app.run(host='0.0.0.0', port=5000, debug=True)