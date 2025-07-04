# Traffic System

A comprehensive traffic system analytics and management platform built with Django (backend) and React (frontend). The project includes video analytics, media management, and real-time data processing, with support for machine learning models and Redis integration.

---

## Project Structure

```
traffic_system/
├── db.sqlite3                  # SQLite database
├── manage.py                   # Django management script
├── media/                      # Uploaded and processed videos
│   ├── processed_videos/
│   ├── uploaded_videos/
│   └── videos/
├── my_model (2).pt             # PyTorch ML model(s)
├── new_application/            # Django app for analytics and management
├── templates/                  # Django HTML templates
│   └── dashboard.html
├── traffic_system/             # Django project core (settings, urls, wsgi, etc.)
├── traffic_system-main/        # React frontend
│   ├── package.json
│   ├── public/
│   └── src/
├── Redis on Windows Release Notes.docx
├── Redis on Windows.docx
├── redis-benchmark.exe         # Redis binaries for Windows
├── redis-cli.exe
├── redis-server.exe
├── ... (other Redis files)
```

---

## Features
- Video upload, processing, and analytics
- Real-time traffic data management
- Machine learning model integration (YoLo)
- Media storage and management
- React-based dashboard and analytics frontend
- Redis support for caching or real-time features

---

## Backend Setup (Django)

1. **Install dependencies:**
   - (Recommended) Create a virtual environment:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```
   - Install Django and other dependencies:
     ```bash
     pip install django djangorestframework opencv-python redis
     ```
   - (Add other dependencies as needed)

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

4. **Access the backend:**
   - Default: http://127.0.0.1:8000/

---

## Frontend Setup (React)

1. **Navigate to the frontend directory:**
   ```bash
   cd traffic_system-main
   ```
2. **Install dependencies:**
   ```bash
   npm install
   ```
3. **Start the React development server:**
   ```bash
   npm start
   ```
4. **Access the frontend:**
   - Default: http://localhost:3000/

---

## Media & Models
- **Media files** (uploaded, processed, and raw videos) are stored in the `media/` directory.
- **Machine learning models** (e.g., `my_model (2).pt`) are used for video analytics and should be placed in the project root or as configured in the code.

---

## Redis (Windows)
- Redis binaries are included for Windows support.
- To start Redis server:
  ```bash
  ./redis-server.exe redis.windows.conf
  ```
- For CLI access:
  ```bash
  ./redis-cli.exe
  ```
- See included documentation files for more details.

---

## Notes
- Update `traffic_system/settings.py` for production (e.g., database, allowed hosts, static/media paths).
- Ensure all dependencies are installed for both backend and frontend.
- For ML features, ensure PyTorch and OpenCV are installed and compatible with your system.
- For Redis features, ensure the server is running before starting Django if required.

---

## License
This project is for educational and research purposes. For commercial use, please contact the repository owner.

---

## Contact
For questions, issues, or contributions, please contact the project maintainer. 
