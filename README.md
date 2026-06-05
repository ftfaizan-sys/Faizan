# 🚌 Bus Tracking System - Full Stack Application

A comprehensive real-time bus tracking solution with user, admin, and driver modules. Built with Python Flask, HTML/CSS/JavaScript, and MongoDB.

## 📋 Features

### User Module
- ✅ User registration and login with JWT authentication
- ✅ View all available buses with real-time status
- ✅ Search buses by route number, source, and destination
- ✅ Live bus tracking on interactive Leaflet.js map with GPS coordinates
- ✅ Estimated arrival time (ETA) calculation using Haversine formula
- ✅ View complete bus, driver, and route information
- ✅ Interactive map with bus stops and route visualization

### Admin Module
- ✅ Secure admin login with role-based access control
- ✅ Add, edit, and delete buses
- ✅ Manage routes and stops
- ✅ Real-time dashboard with statistics (active buses, drivers, users, routes)
- ✅ Monitor all buses on a unified map view
- ✅ View bus status (Running, Delayed, Stopped)
- ✅ Emergency alert management

### Driver Module
- ✅ Driver login with secure authentication
- ✅ Real-time GPS location updates (auto-updates every 10 seconds)
- ✅ Start and stop trip functionality
- ✅ Send emergency alerts to admin with location
- ✅ View current location on interactive map
- ✅ Trip management and status updates

### Map Features
- ✅ Leaflet.js integration for interactive mapping
- ✅ Real-time bus movement tracking
- ✅ Display of bus stops and route paths
- ✅ Auto-refresh location every 5-10 seconds
- ✅ Responsive map design for mobile and desktop
- ✅ Distance and ETA calculations

## 🗄️ Database Schema

```
Collections:
├── users (passengers)
│   ├── name, email, password, phone
│   ├── role (user), created_at, is_active
│
├── drivers
│   ├── name, email, password, phone
│   ├── license_number, is_active, created_at
│
├── buses
│   ├── bus_number, capacity, status
│   ├── route_id, driver_id
│   ├── current_location (latitude, longitude)
│
├── routes
│   ├── route_number, source, destination
│   ├── total_distance, created_at
│
├── stops
│   ├── name, latitude, longitude
│   ├── route_id, stop_order
│
├── location_history
│   ├── bus_id, driver_id
│   ├── latitude, longitude, timestamp
│
└── emergencies
    ├── driver_id, bus_id, message
    ├── timestamp, status
```

## 🛠️ Tech Stack

**Backend:**
- Python 3.8+
- Flask 2.3.0
- Flask-PyMongo (MongoDB integration)
- PyJWT (JWT authentication)
- Werkzeug (password hashing)

**Frontend:**
- HTML5
- CSS3 (Bootstrap 5.3.0)
- JavaScript (Vanilla)
- Leaflet.js (mapping)
- Font Awesome Icons

**Database:**
- MongoDB 4.0+

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- MongoDB running locally or connection string
- pip (Python package manager)
- Git

### Step-by-Step Setup

1. **Clone the Repository**
```bash
git clone https://github.com/ftfaizan-sys/Faizan.git
cd Faizan
git checkout bus-tracking-system
```

2. **Create Virtual Environment**
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment**
```bash
# Create .env file (already provided, update if needed)
# Ensure MongoDB is running on localhost:27017
# Or update MONGO_URI in .env for your MongoDB instance
```

5. **Run the Application**
```bash
python app.py
```

6. **Access in Browser**
```
http://localhost:5000
```

## 🔐 Default Test Credentials

### Regular User
- **Email:** user@test.com
- **Password:** password123

### Admin Account
- **Email:** admin@test.com
- **Password:** admin123

### Driver Account
- **Email:** driver@test.com
- **Password:** driver123

## 🚀 How to Use

### For Users
1. Register or login with your credentials
2. Search for buses by route, source, or destination
3. Click "View Details" to see bus information
4. Select a stop and click "Calculate ETA" for arrival time
5. View real-time bus location on the map

### For Admins
1. Login with admin credentials
2. Access dashboard to view statistics
3. Manage Buses tab: Add, edit, or delete buses
4. Map View tab: Monitor all buses in real-time
5. Emergencies tab: View and manage driver alerts

### For Drivers
1. Login with driver credentials
2. View assigned bus information
3. Click "Start Trip" to begin service
4. Location updates automatically every 10 seconds
5. Click "Emergency" to send alert to admin
6. Click "Stop Trip" to end service

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/admin/auth/login` - Admin login
- `POST /api/driver/auth/login` - Driver login

### User APIs
- `GET /api/buses` - Get all available buses
- `POST /api/buses/search` - Search buses
- `GET /api/buses/<bus_id>/details` - Get bus details
- `GET /api/user/profile` - Get user profile
- `GET /api/tracking/bus/<bus_id>` - Get live tracking data
- `POST /api/tracking/eta` - Calculate ETA

### Admin APIs
- `GET /api/admin/dashboard` - Dashboard statistics
- `POST /api/admin/buses` - Add new bus
- `PUT /api/admin/buses/<bus_id>` - Update bus
- `DELETE /api/admin/buses/<bus_id>` - Delete bus

### Driver APIs
- `POST /api/driver/location` - Update location
- `POST /api/driver/trip/start` - Start trip
- `POST /api/driver/trip/stop` - Stop trip
- `POST /api/driver/emergency` - Send emergency alert

## 🗺️ Map Integration

The application uses **Leaflet.js** for mapping with OpenStreetMap tiles:
- Interactive markers for buses and stops
- Popup information windows
- Distance calculation using Haversine formula
- Real-time location updates
- Route visualization

## 🔒 Security Features

- **JWT Authentication:** Secure token-based authentication
- **Password Hashing:** Bcrypt-style hashing via Werkzeug
- **Role-Based Access Control:** Different permissions for users, admins, drivers
- **Authorization Middleware:** Token validation on protected routes
- **CORS Enabled:** Cross-origin requests handled safely

## 📱 Responsive Design

- Mobile-first approach using Bootstrap 5
- Adaptive UI for all screen sizes
- Touch-friendly buttons and controls
- Optimized map display for mobile devices

## 🐛 Troubleshooting

### MongoDB Connection Error
```
Error: Connection refused at localhost:27017

Solution:
1. Ensure MongoDB is running: `mongod`
2. Or update MONGO_URI in .env with your MongoDB connection string
```

### Port Already in Use
```
Error: Port 5000 already in use

Solution:
1. Edit app.py and change port: `app.run(port=5001)`
2. Or kill the process using the port
```

### Dependencies Installation Issues
```
Solution:
1. Upgrade pip: `pip install --upgrade pip`
2. Install dependencies: `pip install -r requirements.txt`
3. If issues persist, try: `pip install --no-cache-dir -r requirements.txt`
```

### Geolocation Not Working (Drivers)
```
Solution:
1. Ensure browser allows geolocation access
2. Application must be served over HTTPS in production
3. Grant location permission when browser asks
```

## 📊 Sample Data Setup

To add sample data to MongoDB, you can use MongoDB Compass or terminal:

```javascript
// Add sample users
db.users.insertOne({
  name: "John User",
  email: "user@test.com",
  password: "hashed_password",
  phone: "9876543210",
  role: "user",
  created_at: new Date(),
  is_active: true
})

// Add sample buses
db.buses.insertOne({
  bus_number: "BUS-001",
  capacity: 50,
  route_id: ObjectId("..."),
  driver_id: ObjectId("..."),
  status: "Running",
  current_location: {
    latitude: 28.7041,
    longitude: 77.1025,
    updated_at: new Date()
  }
})
```

## 🚀 Deployment

For production deployment:

1. **Environment Variables:**
   - Change `SECRET_KEY` and `JWT_SECRET`
   - Update `MONGO_URI` to production database
   - Set `FLASK_ENV=production`

2. **Security:**
   - Enable HTTPS
   - Set secure CORS origins
   - Use environment-specific configurations

3. **Hosting Options:**
   - Heroku: `git push heroku main`
   - AWS: EC2 with Gunicorn/Nginx
   - DigitalOcean: App Platform
   - Render: Connect GitHub repo

## 📝 Project Structure

```
bus-tracking-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── README.md             # This file
└── (Frontend integrated in app.py)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👨‍💻 Author

**Faizan A Khan**
- GitHub: [@ftfaizan-sys](https://github.com/ftfaizan-sys)
- Email: f2050396@gmail.com

## 🙏 Acknowledgments

- Leaflet.js for mapping functionality
- Bootstrap for responsive design
- MongoDB for flexible database
- Flask community for excellent documentation

## 📞 Support

For issues, questions, or suggestions:
1. Open an issue on GitHub
2. Check existing documentation
3. Review API endpoint details
4. Test with provided credentials

---

**Last Updated:** June 2026  
**Version:** 1.0.0  
**Status:** Production Ready ✅

Happy tracking! 🚌
