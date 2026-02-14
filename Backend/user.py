import bcrypt
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# 1. Ensure User Constraints (Run once)
client = MongoClient("mongodb://localhost:27017/")
db = client.user_storage_db
db.users.create_index("email", unique=True)
db.users.create_index("username", unique=True)

# 2. Registration Route
def signup():
    data = request.get_json()
    
    # Hash the password
    password = data.get('password').encode('utf-8')
    hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt())

    try:
        user_id = db.users.insert_one({
            "username": data.get('username'),
            "email": data.get('email'),
            "password": hashed_pw,
            "role": "operator",  # e.g., 'admin' or 'viewer'
            "assigned_cameras": data.get('cameras', []), # List of CAM_IDs
            "created_at": datetime.utcnow()
        }).inserted_id
        
        return jsonify({"message": "User created", "user_id": str(user_id)}), 201
    except Exception as e:
        return jsonify({"error": "Username or Email already exists"}), 400

# 3. Login Route

def login():
    data = request.get_json()
    user = db.users.find_one({"email": data.get('email')})

    if user and bcrypt.checkpw(data.get('password').encode('utf-8'), user['password']):
        return jsonify({
            "message": "Login successful",
            "username": user['username'],
            "role": user['role']
        }), 200
    
    return jsonify({"error": "Invalid credentials"}), 401