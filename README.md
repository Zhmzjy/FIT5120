# Melbourne Real-Time Parking System 🅿️

A modern web application that provides real-time parking information for Melbourne CBD using government open data.

## 📋 Project Overview

This system displays real-time parking availability across Melbourne CBD with:
- **Live Data**: Integration with Melbourne Government Open Data API
- **Interactive Map**: Modern Vue.js frontend with Leaflet mapping
- **Search Function**: Find parking by postcode or suburb
- **Statistics**: Real-time parking availability statistics
- **Mobile Responsive**: Works on desktop and mobile devices

## 🏗️ Architecture

```
Melbourne Parking System
├── Frontend (Vue.js + Leaflet Maps)
├── Backend API (Flask + MySQL)
├── Database (MySQL with real Melbourne data)
└── Data Source (Melbourne Government Open Data)
```

## 🛠️ Tech Stack

- **Frontend**: Vue.js 3, Leaflet Maps, Modern CSS
- **Backend**: Python Flask, SQLAlchemy ORM
- **Database**: MySQL 8.0
- **Containerization**: Docker & Docker Compose
- **Data Source**: Melbourne Government Open Data API

## 📁 Project Structure

```
FIT5120/
├── frontend/               # Vue.js frontend application
│   ├── src/components/     # Vue components
│   └── public/             # Static assets
├── backend/                # Flask API backend
│   ├── api/                # Modular API structure
│   │   ├── models/         # Database models
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utility functions
│   └── main.py             # Application entry point
├── database/               # Database configuration
│   └── init.sql            # Database initialization script
└── docker-compose.yml      # Docker services configuration
```

## 🚀 Quick Start

### Prerequisites

Make sure you have installed:
- [Docker](https://www.docker.com/get-started) (version 20.0+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd FIT5120
```

### 2. Start the Application

```bash
# Start all services (database, backend, frontend)
docker-compose up --build

# Or run in background mode
docker-compose up --build -d
```

### 3. Wait for Services to Initialize

The system will automatically:
- 🗄️ Initialize MySQL database with Melbourne parking data
- 🔄 Fetch real-time data from Melbourne Government API
- 🌐 Start the web application

**Wait for this message in the logs:**
```
✅ Successfully loaded [X] parking sensors
🌐 Starting Flask application...
```

### 4. Access the Application

- **Web Application**: http://localhost:3000
- **API Documentation**: http://localhost:5001/health
- **Database**: localhost:3307

## 🔧 Development Setup

### For Individual Development

```bash
# Start only the services you need
docker-compose up mysql -d          # Start database only
docker-compose up backend -d        # Start backend only
docker-compose up frontend -d       # Start frontend only
```

### For Team Collaboration

Each team member only needs to run:
```bash
docker-compose up --build
```

No need to install Python, Node.js, or MySQL locally!

## 📊 API Endpoints

### Health Check
- `GET /health/` - System health status
- `GET /health/detailed` - Detailed system diagnostics

### Parking Data
- `GET /api/parking/live` - Real-time parking sensors
- `GET /api/parking/search?q={postcode}` - Search by location
- `POST /api/parking/update` - Refresh data from government API
- `GET /api/parking/zones` - Parking zone information

### Statistics
- `GET /api/stats/` - Overall parking statistics
- `GET /api/stats/zones` - Zone-wise statistics
- `GET /api/stats/parking-lots` - Parking lot information

## 🌐 Data Sources

This application uses **real** Melbourne Government data:
- **API**: Melbourne Open Data Platform
- **Dataset**: On-street Parking Bay Sensors
- **Update Frequency**: Real-time (updated every minute)
- **Coverage**: Melbourne CBD and surrounding areas

## 🛠️ Troubleshooting

### Database Connection Issues

If you see database connection errors:

```bash
# Stop all services
docker-compose down

# Remove volumes and rebuild
docker-compose down -v
docker-compose up --build
```

### Port Conflicts

If ports 3000, 5001, or 3307 are in use:

```bash
# Check what's using the ports
lsof -i :3000
lsof -i :5001
lsof -i :3307

# Kill the processes or modify ports in docker-compose.yml
```

### API Data Issues

If the map shows limited data:

```bash
# Manually refresh data from Melbourne Government API
curl -X POST http://localhost:5001/api/parking/update

# Check system status
curl http://localhost:5001/health/detailed
```

## 📱 Features

### Frontend Features
- 🗺️ **Interactive Map**: Zoom, pan, and click on parking spaces
- 🔍 **Smart Search**: Find parking by postcode or suburb name
- 📊 **Live Statistics**: Real-time availability counters
- 📱 **Mobile Responsive**: Works on all devices
- 🎨 **Modern UI**: Clean, professional interface

### Backend Features
- 🔄 **Auto-Refresh**: Updates data every minute
- 🏗️ **Modular Architecture**: Clean, maintainable code structure
- 📈 **Statistics Engine**: Advanced parking analytics
- 🔗 **API Integration**: Direct connection to Melbourne Government data
- 🛡️ **Error Handling**: Robust error management and fallbacks

## 🔄 Data Flow

1. **Melbourne Government API** → Real-time parking sensor data
2. **Flask Backend** → Processes and stores data in MySQL
3. **Vue.js Frontend** → Displays interactive map with live data
4. **User Interaction** → Search, filter, and view parking information

## 👥 Team Development

### Adding New Features

1. **Frontend Changes**: Edit files in `frontend/src/components/`
2. **Backend API**: Add routes in `backend/api/routes/`
3. **Database**: Modify `database/init.sql` for schema changes
4. **Services**: Add business logic in `backend/api/services/`

### Code Structure

- **Models**: Database entities (`backend/api/models/`)
- **Routes**: API endpoints (`backend/api/routes/`)
- **Services**: Business logic (`backend/api/services/`)
- **Utils**: Helper functions (`backend/api/utils/`)

## 🚀 Deployment

### For Production Deployment

1. **Environment Variables**: Set production database credentials
2. **SSL Configuration**: Add HTTPS certificates
3. **Domain Setup**: Configure your domain name
4. **Scaling**: Use Docker Swarm or Kubernetes

### Environment Variables

Create a `.env` file:
```env
DATABASE_URL=mysql+pymysql://user:password@host/database
FLASK_ENV=production
```

## 📞 Support

### Common Issues

1. **"No parking data"**: Wait for initial data load (2-3 minutes)
2. **"Map not loading"**: Check if port 3000 is accessible
3. **"API errors"**: Verify backend is running on port 5001

### Getting Help

- Check Docker logs: `docker-compose logs [service_name]`
- Verify services: `docker-compose ps`
- Test API: `curl http://localhost:5001/health/`

## 📄 License

This project is developed for educational purposes as part of FIT5120.

---

## 🎯 Quick Commands Reference

```bash
# Start everything
docker-compose up --build

# Start in background
docker-compose up --build -d

# Stop everything
docker-compose down

# View logs
docker-compose logs backend
docker-compose logs frontend

# Restart a service
docker-compose restart backend

# Clean start (removes all data)
docker-compose down -v && docker-compose up --build

# Check service status
docker-compose ps

# Access database directly
docker-compose exec mysql mysql -u root -p fit5120_db
```

## 🔍 Testing the Application

### 1. Verify System Health
```bash
curl http://localhost:5001/health/
```

### 2. Check Real-Time Data
```bash
curl "http://localhost:5001/api/parking/live" | head -20
```

### 3. Test Search Function
```bash
curl "http://localhost:5001/api/parking/search?q=3000"
```

### 4. View Statistics
```bash
curl http://localhost:5001/api/stats/
```

---

**Happy Coding!** 🚀 If you encounter any issues, check the troubleshooting section or review the Docker logs.
