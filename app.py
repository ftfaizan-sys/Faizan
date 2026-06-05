"""
Bus Tracking System - Full Stack Application
Python Flask Backend + HTML/CSS/JavaScript Frontend (All-in-One)
Author: Faizan
Description: Complete bus tracking solution with real-time GPS tracking, admin dashboard, and driver management
"""

from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import datetime
import math
from functools import wraps
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bus_tracking')
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'jwt-secret-key-change-in-production')
app.config['JWT_EXPIRATION'] = 24 * 60 * 60  # 24 hours

# Initialize MongoDB
mongo = PyMongo(app)

# ==================== AUTHENTICATION MIDDLEWARE ====================

def token_required(f):
    """JWT Token validation decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            current_user = data['user_id']
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def generate_token(user_id, role):
    """Generate JWT token"""
    payload = {
        'user_id': str(user_id),
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXPIRATION'])
    }
    token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
    return token

# ==================== DATABASE MODELS / INITIALIZATION ====================

def init_db():
    """Initialize database with collections and indexes"""
    try:
        db = mongo.db
        
        # Create collections with validation
        collections = ['users', 'drivers', 'buses', 'routes', 'stops', 'location_history', 'emergencies']
        
        for collection in collections:
            if collection not in db.list_collection_names():
                db.create_collection(collection)
        
        # Create indexes for better query performance
        db.users.create_index('email', unique=True)
        db.drivers.create_index('email', unique=True)
        db.buses.create_index('bus_number', unique=True)
        db.routes.create_index('route_number', unique=True)
        db.location_history.create_index('bus_id')
        db.emergencies.create_index('driver_id')
        
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# ==================== USER ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validation
        if not data or not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({'message': 'Missing required fields'}), 400
        
        # Check if user exists
        if mongo.db.users.find_one({'email': data['email']}):
            return jsonify({'message': 'User already exists'}), 409
        
        # Hash password
        hashed_password = generate_password_hash(data['password'])
        
        # Create user document
        user = {
            'name': data['name'],
            'email': data['email'],
            'password': hashed_password,
            'phone': data.get('phone', ''),
            'role': 'user',
            'created_at': datetime.datetime.utcnow(),
            'is_active': True
        }
        
        result = mongo.db.users.insert_one(user)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({'message': f'Registration error: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Missing email or password'}), 400
        
        # Find user
        user = mongo.db.users.find_one({'email': data['email']})
        
        if not user or not check_password_hash(user['password'], data['password']):
            return jsonify({'message': 'Invalid email or password'}), 401
        
        if not user['is_active']:
            return jsonify({'message': 'User account is inactive'}), 403
        
        # Generate token
        token = generate_token(str(user['_id']), user['role'])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Login error: {str(e)}'}), 500

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    """Get user profile"""
    try:
        from bson import ObjectId
        user = mongo.db.users.find_one({'_id': ObjectId(current_user)})
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'phone': user.get('phone', ''),
            'role': user['role'],
            'created_at': user['created_at'].isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ==================== BUS ROUTES ====================

@app.route('/api/buses', methods=['GET'])
def get_all_buses():
    """Get all available buses"""
    try:
        buses = list(mongo.db.buses.find({}, {'_id': 1, 'bus_number': 1, 'route_id': 1, 'capacity': 1, 'status': 1, 'current_location': 1, 'driver_id': 1}))
        
        for bus in buses:
            bus['_id'] = str(bus['_id'])
            if bus.get('route_id'):
                bus['route_id'] = str(bus['route_id'])
        
        return jsonify(buses), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/buses/search', methods=['POST'])
def search_buses():
    """Search buses by route, source, or destination"""
    try:
        data = request.get_json()
        
        # Build search query
        query = {}
        
        if data.get('route_number'):
            route = mongo.db.routes.find_one({'route_number': data['route_number']})
            if route:
                query['route_id'] = route['_id']
        
        if data.get('source'):
            query['source'] = {'$regex': data['source'], '$options': 'i'}
        
        if data.get('destination'):
            query['destination'] = {'$regex': data['destination'], '$options': 'i'}
        
        buses = list(mongo.db.buses.find(query))
        
        for bus in buses:
            bus['_id'] = str(bus['_id'])
            if bus.get('route_id'):
                bus['route_id'] = str(bus['route_id'])
        
        return jsonify(buses), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/buses/<bus_id>/details', methods=['GET'])
def get_bus_details(bus_id):
    """Get detailed bus information"""
    try:
        from bson import ObjectId
        
        bus = mongo.db.buses.find_one({'_id': ObjectId(bus_id)})
        
        if not bus:
            return jsonify({'message': 'Bus not found'}), 404
        
        # Get route details
        route = mongo.db.routes.find_one({'_id': bus['route_id']})
        
        # Get driver details
        driver = mongo.db.drivers.find_one({'_id': bus['driver_id']})
        
        # Get stops for route
        stops = list(mongo.db.stops.find({'route_id': bus['route_id']}))
        
        return jsonify({
            'bus': {
                'id': str(bus['_id']),
                'bus_number': bus['bus_number'],
                'capacity': bus['capacity'],
                'status': bus['status'],
                'current_location': bus.get('current_location', {})
            },
            'route': {
                'id': str(route['_id']),
                'route_number': route['route_number'],
                'source': route['source'],
                'destination': route['destination'],
                'total_distance': route['total_distance']
            } if route else None,
            'driver': {
                'id': str(driver['_id']),
                'name': driver['name'],
                'phone': driver['phone'],
                'license_number': driver['license_number']
            } if driver else None,
            'stops': [{'id': str(s['_id']), 'name': s['name'], 'lat': s['latitude'], 'lng': s['longitude']} for s in stops]
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ==================== ADMIN ROUTES ====================

@app.route('/api/admin/auth/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Missing credentials'}), 400
        
        # Find admin user
        admin = mongo.db.users.find_one({'email': data['email'], 'role': 'admin'})
        
        if not admin or not check_password_hash(admin['password'], data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        token = generate_token(str(admin['_id']), 'admin')
        
        return jsonify({
            'message': 'Admin login successful',
            'token': token,
            'admin': {
                'id': str(admin['_id']),
                'name': admin['name'],
                'email': admin['email']
            }
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/buses', methods=['POST'])
@token_required
def add_bus(current_user):
    """Add new bus (Admin only)"""
    try:
        # Check if admin
        if request.current_user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        data = request.get_json()
        
        # Validation
        required_fields = ['bus_number', 'capacity', 'route_id', 'driver_id']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400
        
        from bson import ObjectId
        
        # Check if bus already exists
        if mongo.db.buses.find_one({'bus_number': data['bus_number']}):
            return jsonify({'message': 'Bus already exists'}), 409
        
        bus = {
            'bus_number': data['bus_number'],
            'capacity': int(data['capacity']),
            'route_id': ObjectId(data['route_id']),
            'driver_id': ObjectId(data['driver_id']),
            'status': 'Stopped',
            'current_location': {'latitude': 0, 'longitude': 0},
            'created_at': datetime.datetime.utcnow()
        }
        
        result = mongo.db.buses.insert_one(bus)
        
        return jsonify({
            'message': 'Bus added successfully',
            'bus_id': str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/buses/<bus_id>', methods=['PUT'])
@token_required
def update_bus(current_user, bus_id):
    """Update bus details (Admin only)"""
    try:
        if request.current_user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        from bson import ObjectId
        
        data = request.get_json()
        
        bus = mongo.db.buses.find_one({'_id': ObjectId(bus_id)})
        
        if not bus:
            return jsonify({'message': 'Bus not found'}), 404
        
        # Update allowed fields
        update_fields = {}
        if 'capacity' in data:
            update_fields['capacity'] = int(data['capacity'])
        if 'status' in data:
            update_fields['status'] = data['status']
        
        mongo.db.buses.update_one({'_id': ObjectId(bus_id)}, {'$set': update_fields})
        
        return jsonify({'message': 'Bus updated successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/buses/<bus_id>', methods=['DELETE'])
@token_required
def delete_bus(current_user, bus_id):
    """Delete bus (Admin only)"""
    try:
        if request.current_user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        from bson import ObjectId
        
        result = mongo.db.buses.delete_one({'_id': ObjectId(bus_id)})
        
        if result.deleted_count == 0:
            return jsonify({'message': 'Bus not found'}), 404
        
        return jsonify({'message': 'Bus deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(current_user):
    """Get admin dashboard statistics"""
    try:
        if request.current_user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        # Count statistics
        total_buses = mongo.db.buses.count_documents({})
        active_buses = mongo.db.buses.count_documents({'status': 'Running'})
        total_drivers = mongo.db.drivers.count_documents({})
        total_users = mongo.db.users.count_documents({'role': 'user'})
        total_routes = mongo.db.routes.count_documents({})
        
        return jsonify({
            'total_buses': total_buses,
            'active_buses': active_buses,
            'total_drivers': total_drivers,
            'total_users': total_users,
            'total_routes': total_routes
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ==================== DRIVER ROUTES ====================

@app.route('/api/driver/auth/login', methods=['POST'])
def driver_login():
    """Driver login endpoint"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Missing credentials'}), 400
        
        driver = mongo.db.drivers.find_one({'email': data['email']})
        
        if not driver or not check_password_hash(driver['password'], data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        if not driver['is_active']:
            return jsonify({'message': 'Driver account is inactive'}), 403
        
        token = generate_token(str(driver['_id']), 'driver')
        
        return jsonify({
            'message': 'Driver login successful',
            'token': token,
            'driver': {
                'id': str(driver['_id']),
                'name': driver['name'],
                'email': driver['email']
            }
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/driver/location', methods=['POST'])
@token_required
def update_driver_location(current_user):
    """Update driver's current bus location"""
    try:
        if request.current_user['role'] != 'driver':
            return jsonify({'message': 'Driver access required'}), 403
        
        from bson import ObjectId
        
        data = request.get_json()
        
        if not data.get('latitude') or not data.get('longitude') or not data.get('bus_id'):
            return jsonify({'message': 'Missing location data'}), 400
        
        # Update bus location
        mongo.db.buses.update_one(
            {'_id': ObjectId(data['bus_id'])},
            {'$set': {'current_location': {
                'latitude': float(data['latitude']),
                'longitude': float(data['longitude']),
                'updated_at': datetime.datetime.utcnow()
            }}}
        )
        
        # Save location history
        history = {
            'bus_id': ObjectId(data['bus_id']),
            'driver_id': ObjectId(current_user),
            'latitude': float(data['latitude']),
            'longitude': float(data['longitude']),
            'timestamp': datetime.datetime.utcnow()
        }
        mongo.db.location_history.insert_one(history)
        
        return jsonify({'message': 'Location updated successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/driver/trip/start', methods=['POST'])
@token_required
def start_trip(current_user):
    """Start bus trip"""
    try:
        if request.current_user['role'] != 'driver':
            return jsonify({'message': 'Driver access required'}), 403
        
        from bson import ObjectId
        
        data = request.get_json()
        bus_id = data.get('bus_id')
        
        if not bus_id:
            return jsonify({'message': 'Bus ID required'}), 400
        
        mongo.db.buses.update_one(
            {'_id': ObjectId(bus_id)},
            {'$set': {'status': 'Running'}}
        )
        
        return jsonify({'message': 'Trip started successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/driver/trip/stop', methods=['POST'])
@token_required
def stop_trip(current_user):
    """Stop bus trip"""
    try:
        if request.current_user['role'] != 'driver':
            return jsonify({'message': 'Driver access required'}), 403
        
        from bson import ObjectId
        
        data = request.get_json()
        bus_id = data.get('bus_id')
        
        if not bus_id:
            return jsonify({'message': 'Bus ID required'}), 400
        
        mongo.db.buses.update_one(
            {'_id': ObjectId(bus_id)},
            {'$set': {'status': 'Stopped'}}
        )
        
        return jsonify({'message': 'Trip stopped successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/driver/emergency', methods=['POST'])
@token_required
def send_emergency_alert(current_user):
    """Send emergency alert to admin"""
    try:
        if request.current_user['role'] != 'driver':
            return jsonify({'message': 'Driver access required'}), 403
        
        from bson import ObjectId
        
        data = request.get_json()
        
        emergency = {
            'driver_id': ObjectId(current_user),
            'bus_id': ObjectId(data.get('bus_id')) if data.get('bus_id') else None,
            'message': data.get('message', 'Emergency alert'),
            'timestamp': datetime.datetime.utcnow(),
            'status': 'active'
        }
        
        result = mongo.db.emergencies.insert_one(emergency)
        
        return jsonify({
            'message': 'Emergency alert sent to admin',
            'alert_id': str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ==================== TRACKING & ETA ROUTES ====================

@app.route('/api/tracking/bus/<bus_id>', methods=['GET'])
def get_bus_tracking(bus_id):
    """Get real-time bus tracking data"""
    try:
        from bson import ObjectId
        
        bus = mongo.db.buses.find_one({'_id': ObjectId(bus_id)})
        
        if not bus:
            return jsonify({'message': 'Bus not found'}), 404
        
        # Get route stops
        route = mongo.db.routes.find_one({'_id': bus['route_id']})
        stops = list(mongo.db.stops.find({'route_id': bus['route_id']}).sort('stop_order', 1))
        
        return jsonify({
            'bus': {
                'id': str(bus['_id']),
                'bus_number': bus['bus_number'],
                'status': bus['status'],
                'current_location': bus['current_location']
            },
            'route': {
                'id': str(route['_id']),
                'route_number': route['route_number'],
                'source': route['source'],
                'destination': route['destination']
            } if route else None,
            'stops': [{'id': str(s['_id']), 'name': s['name'], 'latitude': s['latitude'], 'longitude': s['longitude'], 'order': s.get('stop_order', 0)} for s in stops]
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/tracking/eta', methods=['POST'])
def calculate_eta():
    """Calculate estimated arrival time"""
    try:
        data = request.get_json()
        
        from bson import ObjectId
        
        bus_id = data.get('bus_id')
        stop_id = data.get('stop_id')
        
        if not bus_id or not stop_id:
            return jsonify({'message': 'Missing parameters'}), 400
        
        bus = mongo.db.buses.find_one({'_id': ObjectId(bus_id)})
        stop = mongo.db.stops.find_one({'_id': ObjectId(stop_id)})
        
        if not bus or not stop:
            return jsonify({'message': 'Bus or stop not found'}), 404
        
        # Calculate distance using Haversine formula
        current_lat = bus['current_location']['latitude']
        current_lng = bus['current_location']['longitude']
        stop_lat = stop['latitude']
        stop_lng = stop['longitude']
        
        distance = haversine_distance(current_lat, current_lng, stop_lat, stop_lng)
        
        # Assume average speed of 40 km/h
        avg_speed = 40
        eta_minutes = (distance / avg_speed) * 60
        
        eta_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=eta_minutes)
        
        return jsonify({
            'distance_km': round(distance, 2),
            'eta_minutes': round(eta_minutes, 2),
            'eta_time': eta_time.isoformat(),
            'stop_name': stop['name']
        }), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

# ==================== FRONTEND ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bus Tracking System</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://leafletjs.com/dist/leaflet.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 1rem 2rem;
        }
        
        .navbar .brand {
            font-size: 1.5rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .container-main {
            margin-top: 2rem;
            margin-bottom: 3rem;
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            overflow: hidden;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .form-section {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .input-group {
            margin-bottom: 1.5rem;
        }
        
        .form-label {
            color: #333;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .form-control {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            transition: border-color 0.3s;
        }
        
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 500;
            transition: transform 0.2s;
        }
        
        .btn-primary:hover {
            transform: scale(1.02);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        
        .stat-card h3 {
            font-size: 2rem;
            font-weight: bold;
        }
        
        .stat-card p {
            margin: 0;
            opacity: 0.9;
        }
        
        .map-container {
            height: 400px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        #map {
            height: 100%;
            width: 100%;
        }
        
        .bus-item {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
            transition: all 0.3s;
        }
        
        .bus-item:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .badge-status {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .badge-running {
            background: #10b981;
            color: white;
        }
        
        .badge-stopped {
            background: #ef4444;
            color: white;
        }
        
        .badge-delayed {
            background: #f59e0b;
            color: white;
        }
        
        .section-title {
            color: white;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .tab-content {
            background: white;
            border-radius: 12px;
            padding: 2rem;
        }
        
        .nav-tabs {
            border-bottom: 2px solid #e0e0e0;
        }
        
        .nav-link {
            color: #666;
            border: none;
            font-weight: 500;
        }
        
        .nav-link.active {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            background: none;
        }
        
        .alert-custom {
            border: none;
            border-radius: 10px;
        }
        
        .loader {
            display: none;
            text-align: center;
            padding: 2rem;
        }
        
        .spinner-border {
            color: #667eea;
        }
        
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar sticky-top">
        <div class="container-fluid">
            <span class="brand"><i class="fas fa-bus"></i> Bus Tracking System</span>
            <div class="d-flex align-items-center gap-2">
                <span id="userDisplay" class="me-3"></span>
                <button class="btn btn-sm btn-outline-danger" onclick="logout()"><i class="fas fa-sign-out-alt"></i> Logout</button>
            </div>
        </div>
    </nav>

    <!-- Main Container -->
    <div class="container-main container-fluid">
        
        <!-- Auth Section -->
        <div id="authSection" class="row">
            <div class="col-md-4 mx-auto">
                <div class="form-section">
                    <h2 class="text-center mb-4">Bus Tracking System</h2>
                    
                    <!-- Auth Tabs -->
                    <ul class="nav nav-tabs" role="tablist">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" href="#loginTab" role="tab">Login</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#registerTab" role="tab">Register</a>
                        </li>
                    </ul>
                    
                    <div class="tab-content mt-3">
                        <!-- Login Tab -->
                        <div id="loginTab" class="tab-pane fade show active" role="tabpanel">
                            <div class="input-group">
                                <label class="form-label">Email</label>
                                <input type="email" id="loginEmail" class="form-control" placeholder="Enter email">
                            </div>
                            <div class="input-group">
                                <label class="form-label">Password</label>
                                <input type="password" id="loginPassword" class="form-control" placeholder="Enter password">
                            </div>
                            <button class="btn btn-primary w-100 mb-2" onclick="userLogin()">Login</button>
                            <button class="btn btn-outline-primary w-100 mb-2" onclick="adminLoginModal()">Admin Login</button>
                            <button class="btn btn-outline-success w-100" onclick="driverLoginModal()">Driver Login</button>
                        </div>
                        
                        <!-- Register Tab -->
                        <div id="registerTab" class="tab-pane fade" role="tabpanel">
                            <div class="input-group">
                                <label class="form-label">Full Name</label>
                                <input type="text" id="regName" class="form-control" placeholder="Enter your name">
                            </div>
                            <div class="input-group">
                                <label class="form-label">Email</label>
                                <input type="email" id="regEmail" class="form-control" placeholder="Enter email">
                            </div>
                            <div class="input-group">
                                <label class="form-label">Phone</label>
                                <input type="tel" id="regPhone" class="form-control" placeholder="Enter phone number">
                            </div>
                            <div class="input-group">
                                <label class="form-label">Password</label>
                                <input type="password" id="regPassword" class="form-control" placeholder="Enter password">
                            </div>
                            <button class="btn btn-primary w-100" onclick="registerUser()">Register</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- User Dashboard -->
        <div id="userDashboard" class="hidden">
            <h2 class="section-title"><i class="fas fa-user"></i> Passenger Dashboard</h2>
            
            <!-- Search Section -->
            <div class="row mb-4">
                <div class="col-md-8 mx-auto">
                    <div class="form-section">
                        <h5 class="mb-3"><i class="fas fa-search"></i> Search Buses</h5>
                        <div class="row">
                            <div class="col-md-4">
                                <input type="text" id="searchRoute" class="form-control" placeholder="Route Number">
                            </div>
                            <div class="col-md-4">
                                <input type="text" id="searchSource" class="form-control" placeholder="Source">
                            </div>
                            <div class="col-md-4">
                                <input type="text" id="searchDestination" class="form-control" placeholder="Destination">
                            </div>
                        </div>
                        <button class="btn btn-primary w-100 mt-3" onclick="searchBuses()"><i class="fas fa-search"></i> Search</button>
                    </div>
                </div>
            </div>
            
            <!-- Buses List -->
            <div class="row">
                <div class="col-md-10 mx-auto">
                    <h5 class="text-white mb-3"><i class="fas fa-bus"></i> Available Buses</h5>
                    <div id="busesList" class="loader">
                        <div class="spinner-border" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bus Details Modal -->
        <div id="busDetailsModal" class="hidden">
            <div class="row">
                <div class="col-md-10 mx-auto">
                    <button class="btn btn-outline-light mb-3" onclick="showUserDashboard()"><i class="fas fa-arrow-left"></i> Back</button>
                    <div class="form-section">
                        <h3 id="busTitle" class="mb-3"></h3>
                        <div class="row">
                            <div class="col-md-6">
                                <h5>Bus Information</h5>
                                <p><strong>Bus Number:</strong> <span id="detailBusNumber"></span></p>
                                <p><strong>Capacity:</strong> <span id="detailCapacity"></span> Passengers</p>
                                <p><strong>Status:</strong> <span id="detailStatus" class="badge"></span></p>
                            </div>
                            <div class="col-md-6">
                                <h5>Route Information</h5>
                                <p><strong>Route:</strong> <span id="detailRoute"></span></p>
                                <p><strong>Source:</strong> <span id="detailSource"></span></p>
                                <p><strong>Destination:</strong> <span id="detailDestination"></span></p>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <h5>Driver Information</h5>
                                <p><strong>Name:</strong> <span id="detailDriverName"></span></p>
                                <p><strong>Phone:</strong> <span id="detailDriverPhone"></span></p>
                                <p><strong>License:</strong> <span id="detailLicense"></span></p>
                            </div>
                            <div class="col-md-6">
                                <h5>ETA Calculation</h5>
                                <div class="form-group mb-3">
                                    <label class="form-label">Select Stop</label>
                                    <select id="stopSelect" class="form-control">
                                        <option>Choose a stop</option>
                                    </select>
                                </div>
                                <button class="btn btn-primary" onclick="calculateETA()"><i class="fas fa-clock"></i> Calculate ETA</button>
                                <div id="etaResult" class="mt-3"></div>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <h5>Route Map</h5>
                        <div class="map-container">
                            <div id="detailMap"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Admin Dashboard -->
        <div id="adminDashboard" class="hidden">
            <h2 class="section-title"><i class="fas fa-th-large"></i> Admin Dashboard</h2>
            
            <!-- Statistics -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="stat-card">
                        <h3 id="totalBuses">0</h3>
                        <p>Total Buses</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <h3 id="activeBuses">0</h3>
                        <p>Active Buses</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <h3 id="totalDrivers">0</h3>
                        <p>Total Drivers</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <h3 id="totalUsers">0</h3>
                        <p>Total Users</p>
                    </div>
                </div>
            </div>
            
            <!-- Admin Tabs -->
            <div class="row">
                <div class="col-md-12">
                    <ul class="nav nav-tabs mb-3" role="tablist">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" href="#busMgmt" role="tab">Manage Buses</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#mapView" role="tab">Map View</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#emergencies" role="tab">Emergencies</a>
                        </li>
                    </ul>
                    
                    <div class="tab-content">
                        <!-- Bus Management -->
                        <div id="busMgmt" class="tab-pane fade show active" role="tabpanel">
                            <div class="form-section mb-4">
                                <h5 class="mb-3"><i class="fas fa-plus"></i> Add New Bus</h5>
                                <div class="row">
                                    <div class="col-md-6">
                                        <input type="text" id="busNumber" class="form-control mb-2" placeholder="Bus Number">
                                        <input type="number" id="busCapacity" class="form-control mb-2" placeholder="Capacity">
                                        <input type="text" id="busRoute" class="form-control mb-2" placeholder="Route ID">
                                    </div>
                                    <div class="col-md-6">
                                        <input type="text" id="busDriver" class="form-control mb-2" placeholder="Driver ID">
                                        <select id="busStatus" class="form-control mb-2">
                                            <option>Running</option>
                                            <option>Stopped</option>
                                            <option>Delayed</option>
                                        </select>
                                        <button class="btn btn-primary w-100" onclick="addBus()"><i class="fas fa-plus"></i> Add Bus</button>
                                    </div>
                                </div>
                            </div>
                            
                            <h5><i class="fas fa-list"></i> All Buses</h5>
                            <div id="adminBusesList"></div>
                        </div>
                        
                        <!-- Map View -->
                        <div id="mapView" class="tab-pane fade" role="tabpanel">
                            <div class="map-container" style="height: 500px;">
                                <div id="adminMap"></div>
                            </div>
                        </div>
                        
                        <!-- Emergencies -->
                        <div id="emergencies" class="tab-pane fade" role="tabpanel">
                            <h5><i class="fas fa-exclamation-triangle"></i> Emergency Alerts</h5>
                            <div id="emergenciesList" class="mt-3"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Driver Dashboard -->
        <div id="driverDashboard" class="hidden">
            <h2 class="section-title"><i class="fas fa-steering-wheel"></i> Driver Dashboard</h2>
            
            <div class="row mb-4">
                <div class="col-md-8 mx-auto">
                    <div class="form-section">
                        <h5 class="mb-3"><i class="fas fa-bus"></i> My Bus</h5>
                        <div id="myBusInfo" class="mb-3"></div>
                        
                        <div class="row">
                            <div class="col-md-4">
                                <button class="btn btn-success w-100 mb-2" id="startBtn" onclick="startTrip()"><i class="fas fa-play"></i> Start Trip</button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-warning w-100 mb-2" id="stopBtn" onclick="stopTrip()"><i class="fas fa-stop"></i> Stop Trip</button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-danger w-100 mb-2" onclick="sendEmergency()"><i class="fas fa-exclamation"></i> Emergency</button>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <h5>Current Location</h5>
                        <div class="map-container" style="height: 300px;">
                            <div id="driverMap"></div>
                        </div>
                        
                        <div class="mt-3">
                            <p><strong>Latitude:</strong> <span id="driverLat">-</span></p>
                            <p><strong>Longitude:</strong> <span id="driverLng">-</span></p>
                            <button class="btn btn-info w-100" onclick="updateLocation()"><i class="fas fa-location-dot"></i> Update Location</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Scripts -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <script>
        // Global Variables
        const API_BASE = '/api';
        let authToken = localStorage.getItem('authToken');
        let userRole = localStorage.getItem('userRole');
        let userId = localStorage.getItem('userId');
        let currentBusId = null;
        let currentBusData = null;
        let maps = {};

        // ==================== UTILITY FUNCTIONS ====================

        function showAlert(message, type = 'info') {
            const alertHtml = `
                <div class="alert alert-${type} alert-custom alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            const alertContainer = document.createElement('div');
            alertContainer.innerHTML = alertHtml;
            document.body.insertBefore(alertContainer.firstChild, document.body.firstChild);
            
            setTimeout(() => {
                document.querySelector('.alert')?.remove();
            }, 5000);
        }

        function makeRequest(method, endpoint, data = null) {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            if (authToken) {
                options.headers['Authorization'] = `Bearer ${authToken}`;
            }

            if (data) {
                options.body = JSON.stringify(data);
            }

            return fetch(`${API_BASE}${endpoint}`, options)
                .then(response => response.json())
                .catch(error => {
                    console.error('Request error:', error);
                    return { message: 'Network error' };
                });
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString();
        }

        // ==================== AUTHENTICATION ====================

        function userLogin() {
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;

            if (!email || !password) {
                showAlert('Please enter email and password', 'warning');
                return;
            }

            makeRequest('POST', '/auth/login', { email, password })
                .then(response => {
                    if (response.token) {
                        authToken = response.token;
                        userId = response.user.id;
                        userRole = 'user';
                        localStorage.setItem('authToken', authToken);
                        localStorage.setItem('userRole', userRole);
                        localStorage.setItem('userId', userId);
                        
                        showAlert('Login successful!', 'success');
                        showUserDashboard();
                    } else {
                        showAlert(response.message || 'Login failed', 'danger');
                    }
                });
        }

        function registerUser() {
            const name = document.getElementById('regName').value;
            const email = document.getElementById('regEmail').value;
            const phone = document.getElementById('regPhone').value;
            const password = document.getElementById('regPassword').value;

            if (!name || !email || !password) {
                showAlert('Please fill all required fields', 'warning');
                return;
            }

            makeRequest('POST', '/auth/register', { name, email, phone, password })
                .then(response => {
                    if (response.user_id) {
                        showAlert('Registration successful! Please login.', 'success');
                        document.getElementById('regName').value = '';
                        document.getElementById('regEmail').value = '';
                        document.getElementById('regPhone').value = '';
                        document.getElementById('regPassword').value = '';
                    } else {
                        showAlert(response.message || 'Registration failed', 'danger');
                    }
                });
        }

        function adminLoginModal() {
            const email = prompt('Enter admin email:');
            if (!email) return;
            
            const password = prompt('Enter admin password:');
            if (!password) return;

            makeRequest('POST', '/admin/auth/login', { email, password })
                .then(response => {
                    if (response.token) {
                        authToken = response.token;
                        userId = response.admin.id;
                        userRole = 'admin';
                        localStorage.setItem('authToken', authToken);
                        localStorage.setItem('userRole', userRole);
                        localStorage.setItem('userId', userId);
                        
                        showAlert('Admin login successful!', 'success');
                        showAdminDashboard();
                    } else {
                        showAlert(response.message || 'Login failed', 'danger');
                    }
                });
        }

        function driverLoginModal() {
            const email = prompt('Enter driver email:');
            if (!email) return;
            
            const password = prompt('Enter driver password:');
            if (!password) return;

            makeRequest('POST', '/driver/auth/login', { email, password })
                .then(response => {
                    if (response.token) {
                        authToken = response.token;
                        userId = response.driver.id;
                        userRole = 'driver';
                        localStorage.setItem('authToken', authToken);
                        localStorage.setItem('userRole', userRole);
                        localStorage.setItem('userId', userId);
                        
                        showAlert('Driver login successful!', 'success');
                        showDriverDashboard();
                    } else {
                        showAlert(response.message || 'Login failed', 'danger');
                    }
                });
        }

        function logout() {
            localStorage.clear();
            authToken = null;
            userRole = null;
            userId = null;
            location.reload();
        }

        // ==================== UI NAVIGATION ====================

        function hideAll() {
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('userDashboard').classList.add('hidden');
            document.getElementById('busDetailsModal').classList.add('hidden');
            document.getElementById('adminDashboard').classList.add('hidden');
            document.getElementById('driverDashboard').classList.add('hidden');
        }

        function showUserDashboard() {
            hideAll();
            document.getElementById('userDashboard').classList.remove('hidden');
            document.getElementById('userDisplay').textContent = `Logged in as: ${userRole}`;
            getAllBuses();
        }

        function showAdminDashboard() {
            hideAll();
            document.getElementById('adminDashboard').classList.remove('hidden');
            document.getElementById('userDisplay').textContent = `Logged in as: Admin`;
            loadAdminDashboard();
        }

        function showDriverDashboard() {
            hideAll();
            document.getElementById('driverDashboard').classList.remove('hidden');
            document.getElementById('userDisplay').textContent = `Logged in as: Driver`;
            loadDriverDashboard();
        }

        // ==================== USER DASHBOARD ====================

        function getAllBuses() {
            document.getElementById('busesList').innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';

            makeRequest('GET', '/buses')
                .then(response => {
                    if (Array.isArray(response)) {
                        let html = '';
                        if (response.length === 0) {
                            html = '<div class="alert alert-info">No buses available</div>';
                        } else {
                            response.forEach(bus => {
                                const statusClass = bus.status === 'Running' ? 'badge-running' : 
                                                  bus.status === 'Delayed' ? 'badge-delayed' : 'badge-stopped';
                                html += `
                                    <div class="bus-item">
                                        <div class="row align-items-center">
                                            <div class="col-md-6">
                                                <h5><i class="fas fa-bus"></i> ${bus.bus_number}</h5>
                                                <p><strong>Capacity:</strong> ${bus.capacity} passengers</p>
                                            </div>
                                            <div class="col-md-3">
                                                <span class="badge-status ${statusClass}">${bus.status}</span>
                                            </div>
                                            <div class="col-md-3">
                                                <button class="btn btn-sm btn-primary" onclick="viewBusDetails('${bus._id}')">
                                                    <i class="fas fa-info-circle"></i> View Details
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        document.getElementById('busesList').innerHTML = html;
                    }
                });
        }

        function searchBuses() {
            const route = document.getElementById('searchRoute').value;
            const source = document.getElementById('searchSource').value;
            const destination = document.getElementById('searchDestination').value;

            makeRequest('POST', '/buses/search', { route_number: route, source, destination })
                .then(response => {
                    if (Array.isArray(response)) {
                        let html = '';
                        if (response.length === 0) {
                            html = '<div class="alert alert-warning">No buses found</div>';
                        } else {
                            response.forEach(bus => {
                                const statusClass = bus.status === 'Running' ? 'badge-running' : 
                                                  bus.status === 'Delayed' ? 'badge-delayed' : 'badge-stopped';
                                html += `
                                    <div class="bus-item">
                                        <div class="row align-items-center">
                                            <div class="col-md-6">
                                                <h5><i class="fas fa-bus"></i> ${bus.bus_number}</h5>
                                                <p><strong>Capacity:</strong> ${bus.capacity}</p>
                                            </div>
                                            <div class="col-md-3">
                                                <span class="badge-status ${statusClass}">${bus.status}</span>
                                            </div>
                                            <div class="col-md-3">
                                                <button class="btn btn-sm btn-primary" onclick="viewBusDetails('${bus._id}')">View Details</button>
                                            </div>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        document.getElementById('busesList').innerHTML = html;
                        showAlert('Search completed', 'info');
                    }
                });
        }

        function viewBusDetails(busId) {
            currentBusId = busId;

            makeRequest('GET', `/buses/${busId}/details`)
                .then(response => {
                    if (response.bus) {
                        currentBusData = response;

                        // Populate fields
                        document.getElementById('busTitle').textContent = `Bus ${response.bus.bus_number} Details`;
                        document.getElementById('detailBusNumber').textContent = response.bus.bus_number;
                        document.getElementById('detailCapacity').textContent = response.bus.capacity;
                        document.getElementById('detailStatus').textContent = response.bus.status;
                        document.getElementById('detailStatus').className = 'badge ' + 
                            (response.bus.status === 'Running' ? 'badge-success' : 
                             response.bus.status === 'Delayed' ? 'badge-warning' : 'badge-danger');

                        if (response.route) {
                            document.getElementById('detailRoute').textContent = response.route.route_number;
                            document.getElementById('detailSource').textContent = response.route.source;
                            document.getElementById('detailDestination').textContent = response.route.destination;
                        }

                        if (response.driver) {
                            document.getElementById('detailDriverName').textContent = response.driver.name;
                            document.getElementById('detailDriverPhone').textContent = response.driver.phone;
                            document.getElementById('detailLicense').textContent = response.driver.license_number;
                        }

                        // Populate stops
                        let stopOptions = '<option>Choose a stop</option>';
                        response.stops.forEach(stop => {
                            stopOptions += `<option value="${stop.id}">${stop.name}</option>`;
                        });
                        document.getElementById('stopSelect').innerHTML = stopOptions;

                        // Initialize map
                        initializeDetailMap(response);

                        document.getElementById('userDashboard').classList.add('hidden');
                        document.getElementById('busDetailsModal').classList.remove('hidden');
                    }
                });
        }

        function initializeDetailMap(busData) {
            if (maps.detail) {
                maps.detail.remove();
            }

            maps.detail = L.map('detailMap').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(maps.detail);

            // Add bus marker
            if (busData.bus.current_location.latitude !== 0) {
                L.marker([busData.bus.current_location.latitude, busData.bus.current_location.longitude])
                    .bindPopup(`<b>${busData.bus.bus_number}</b><br>Status: ${busData.bus.status}`)
                    .addTo(maps.detail);
            }

            // Add stops
            busData.stops.forEach(stop => {
                L.circleMarker([stop.lat, stop.lng], { color: 'blue', radius: 5 })
                    .bindPopup(`<b>${stop.name}</b>`)
                    .addTo(maps.detail);
            });
        }

        function calculateETA() {
            const stopId = document.getElementById('stopSelect').value;

            if (stopId === '') {
                showAlert('Please select a stop', 'warning');
                return;
            }

            makeRequest('POST', '/tracking/eta', { bus_id: currentBusId, stop_id: stopId })
                .then(response => {
                    if (response.eta_time) {
                        const resultHtml = `
                            <div class="alert alert-success">
                                <h6><i class="fas fa-check-circle"></i> ETA Calculated</h6>
                                <p><strong>Stop:</strong> ${response.stop_name}</p>
                                <p><strong>Distance:</strong> ${response.distance_km} km</p>
                                <p><strong>Time:</strong> ${response.eta_minutes} minutes</p>
                                <p><strong>Arrival:</strong> ${new Date(response.eta_time).toLocaleTimeString()}</p>
                            </div>
                        `;
                        document.getElementById('etaResult').innerHTML = resultHtml;
                    } else {
                        showAlert(response.message || 'ETA calculation failed', 'danger');
                    }
                });
        }

        // ==================== ADMIN DASHBOARD ====================

        function loadAdminDashboard() {
            makeRequest('GET', '/admin/dashboard')
                .then(response => {
                    if (response.total_buses !== undefined) {
                        document.getElementById('totalBuses').textContent = response.total_buses;
                        document.getElementById('activeBuses').textContent = response.active_buses;
                        document.getElementById('totalDrivers').textContent = response.total_drivers;
                        document.getElementById('totalUsers').textContent = response.total_users;
                    }
                });

            loadAdminBuses();
            initializeAdminMap();
        }

        function loadAdminBuses() {
            makeRequest('GET', '/buses')
                .then(response => {
                    if (Array.isArray(response)) {
                        let html = '';
                        response.forEach(bus => {
                            const statusClass = bus.status === 'Running' ? 'badge-running' : 
                                              bus.status === 'Delayed' ? 'badge-delayed' : 'badge-stopped';
                            html += `
                                <div class="bus-item">
                                    <div class="row align-items-center">
                                        <div class="col-md-4">
                                            <h6><i class="fas fa-bus"></i> ${bus.bus_number}</h6>
                                            <small>Capacity: ${bus.capacity}</small>
                                        </div>
                                        <div class="col-md-3">
                                            <span class="badge-status ${statusClass}">${bus.status}</span>
                                        </div>
                                        <div class="col-md-2">
                                            <button class="btn btn-sm btn-warning" onclick="editBusModal('${bus._id}')"><i class="fas fa-edit"></i> Edit</button>
                                        </div>
                                        <div class="col-md-2">
                                            <button class="btn btn-sm btn-danger" onclick="deleteBus('${bus._id}')"><i class="fas fa-trash"></i> Delete</button>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        document.getElementById('adminBusesList').innerHTML = html;
                    }
                });
        }

        function addBus() {
            const busNumber = document.getElementById('busNumber').value;
            const capacity = document.getElementById('busCapacity').value;
            const routeId = document.getElementById('busRoute').value;
            const driverId = document.getElementById('busDriver').value;
            const status = document.getElementById('busStatus').value;

            if (!busNumber || !capacity || !routeId || !driverId) {
                showAlert('Please fill all fields', 'warning');
                return;
            }

            makeRequest('POST', '/admin/buses', { bus_number: busNumber, capacity, route_id: routeId, driver_id: driverId, status })
                .then(response => {
                    if (response.bus_id) {
                        showAlert('Bus added successfully', 'success');
                        document.getElementById('busNumber').value = '';
                        document.getElementById('busCapacity').value = '';
                        document.getElementById('busRoute').value = '';
                        document.getElementById('busDriver').value = '';
                        loadAdminBuses();
                    } else {
                        showAlert(response.message || 'Failed to add bus', 'danger');
                    }
                });
        }

        function deleteBus(busId) {
            if (confirm('Are you sure you want to delete this bus?')) {
                makeRequest('DELETE', `/admin/buses/${busId}`)
                    .then(response => {
                        if (response.message === 'Bus deleted successfully') {
                            showAlert('Bus deleted successfully', 'success');
                            loadAdminBuses();
                        } else {
                            showAlert(response.message || 'Failed to delete bus', 'danger');
                        }
                    });
            }
        }

        function initializeAdminMap() {
            if (maps.admin) {
                maps.admin.remove();
            }

            maps.admin = L.map('adminMap').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(maps.admin);

            // Load and display all buses
            makeRequest('GET', '/buses')
                .then(response => {
                    if (Array.isArray(response)) {
                        response.forEach(bus => {
                            if (bus.current_location && bus.current_location.latitude !== 0) {
                                const color = bus.status === 'Running' ? 'green' : 'red';
                                L.marker([bus.current_location.latitude, bus.current_location.longitude], {
                                    icon: L.icon({
                                        iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBmaWxsPSJncmVlbiIgZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6bTAgMThjLTQuNDEgMC04LTMuNTktOC04czMuNTktOCA4LTggOCAzLjU5IDggOC0zLjU5IDgtOCA4eiIvPjwvc3ZnPg==',
                                        iconSize: [25, 25]
                                    })
                                })
                                .bindPopup(`<b>${bus.bus_number}</b><br>Status: ${bus.status}`)
                                .addTo(maps.admin);
                            }
                        });
                    }
                });
        }

        // ==================== DRIVER DASHBOARD ====================

        function loadDriverDashboard() {
            // Load driver's bus (You would typically get this from the backend)
            makeRequest('GET', '/buses')
                .then(response => {
                    if (Array.isArray(response) && response.length > 0) {
                        const bus = response[0]; // Assuming first bus is driver's bus
                        const html = `
                            <div class="alert alert-info">
                                <h6><i class="fas fa-bus"></i> Bus: ${bus.bus_number}</h6>
                                <p><strong>Capacity:</strong> ${bus.capacity} passengers</p>
                                <p><strong>Status:</strong> <span class="badge badge-${bus.status === 'Running' ? 'success' : 'danger'}">${bus.status}</span></p>
                            </div>
                        `;
                        document.getElementById('myBusInfo').innerHTML = html;
                        currentBusId = bus._id;
                    }
                });

            // Initialize driver map
            initializeDriverMap();

            // Auto-update location every 10 seconds
            setInterval(updateLocationAuto, 10000);
        }

        function initializeDriverMap() {
            if (maps.driver) {
                maps.driver.remove();
            }

            maps.driver = L.map('driverMap').setView([28.7041, 77.1025], 10);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(maps.driver);

            // Get current location
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(position => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    document.getElementById('driverLat').textContent = lat.toFixed(4);
                    document.getElementById('driverLng').textContent = lng.toFixed(4);
                    maps.driver.setView([lat, lng], 13);
                    L.marker([lat, lng]).addTo(maps.driver).bindPopup('Your Location').openPopup();
                });
            }
        }

        function updateLocationAuto() {
            if (navigator.geolocation && currentBusId) {
                navigator.geolocation.getCurrentPosition(position => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    makeRequest('POST', '/driver/location', {
                        bus_id: currentBusId,
                        latitude: lat,
                        longitude: lng
                    });
                });
            }
        }

        function updateLocation() {
            if (navigator.geolocation && currentBusId) {
                navigator.geolocation.getCurrentPosition(position => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    makeRequest('POST', '/driver/location', {
                        bus_id: currentBusId,
                        latitude: lat,
                        longitude: lng
                    })
                    .then(response => {
                        if (response.message) {
                            showAlert('Location updated successfully', 'success');
                            document.getElementById('driverLat').textContent = lat.toFixed(4);
                            document.getElementById('driverLng').textContent = lng.toFixed(4);
                            maps.driver.setView([lat, lng], 13);
                        }
                    });
                });
            } else {
                showAlert('Geolocation not available', 'warning');
            }
        }

        function startTrip() {
            makeRequest('POST', '/driver/trip/start', { bus_id: currentBusId })
                .then(response => {
                    if (response.message.includes('successfully')) {
                        showAlert('Trip started!', 'success');
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('stopBtn').disabled = false;
                        loadDriverDashboard();
                    }
                });
        }

        function stopTrip() {
            makeRequest('POST', '/driver/trip/stop', { bus_id: currentBusId })
                .then(response => {
                    if (response.message.includes('successfully')) {
                        showAlert('Trip stopped!', 'warning');
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                        loadDriverDashboard();
                    }
                });
        }

        function sendEmergency() {
            const message = prompt('Enter emergency message:', 'Emergency Alert');
            if (message) {
                makeRequest('POST', '/driver/emergency', { bus_id: currentBusId, message })
                    .then(response => {
                        if (response.alert_id) {
                            showAlert('Emergency alert sent to admin!', 'danger');
                        }
                    });
            }
        }

        // ==================== INITIALIZATION ====================

        window.addEventListener('load', () => {
            if (authToken && userRole) {
                switch(userRole) {
                    case 'user':
                        showUserDashboard();
                        break;
                    case 'admin':
                        showAdminDashboard();
                        break;
                    case 'driver':
                        showDriverDashboard();
                        break;
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve frontend"""
    return render_template_string(HTML_TEMPLATE)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'message': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Add sample data (optional)
    print("Bus Tracking System Started!")
    print("Access the application at: http://localhost:5000")
    print("\nTest Credentials:")
    print("User - Email: user@test.com | Password: password123")
    print("Admin - Email: admin@test.com | Password: admin123")
    print("Driver - Email: driver@test.com | Password: driver123")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
