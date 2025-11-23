# How to Run the Backend and Frontend for API Testing

## Prerequisites

- Python 3.9+ installed
- Node.js installed
- Virtual environment created (`.venv` folder exists in root)

## Quick Start (Automated)

### Option 1: Use the Batch Scripts (Easiest)

1. **Start Backend** (Terminal 1):

   ```bash
   # Activate virtual environment first
   .\.venv\Scripts\activate

   # Run the backend startup script
   .\start_backend.bat
   ```

   The backend will start at: `http://localhost:8000`

   - API Docs: `http://localhost:8000/docs`
   - API Base: `http://localhost:8000/api`

2. **Start Frontend** (Terminal 2):

   ```bash
   cd Frontend
   npm run dev
   ```

   The frontend will start at: `http://localhost:5173`

   - Test Page: `http://localhost:5173/test`

## Manual Setup (Step by Step)

### Backend Setup

1. **Activate Virtual Environment**:

   ```powershell
   .\.venv\Scripts\activate
   ```

2. **Install Dependencies** (if not already installed):

   ```powershell
   pip install -r requirements.txt
   ```

3. **Start the Backend Server**:

   ```powershell
   python -m uvicorn bs.src.app:app --reload --host 0.0.0.0 --port 8000
   ```

   The server will start at `http://localhost:8000`

4. **Verify Backend is Running**:
   - Open browser: `http://localhost:8000/health`
   - You should see: `{"status": "ok", "phase": 2, "time": ...}`
   - API Documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to Frontend Directory**:

   ```powershell
   cd Frontend
   ```

2. **Install Dependencies** (if not already installed):

   ```powershell
   npm install
   ```

3. **Start the Development Server**:

   ```powershell
   npm run dev
   ```

   The frontend will start at `http://localhost:5173`

4. **Access the Test Page**:
   - Open browser: `http://localhost:5173/test`

## Testing the API

### Using the Test/Debug Page

1. Navigate to: `http://localhost:5173/test`

2. The page provides tabs for testing all API endpoints:

   - **List Artifacts**: POST `/api/artifacts`
   - **Ingest Artifact**: POST `/api/artifact/{type}`
   - **Search by Regex**: POST `/api/artifact/byRegEx`
   - **Get Artifact**: GET `/api/artifact/{type}/{id}`
   - **Get by Name**: GET `/api/artifact/byName/{name}`
   - **Get All Artifacts**: GET `/api/artifact`
   - **Utility**: Health, Tracks, Reset endpoints

3. Each tab has form fields to input data
4. Results display in the right console panel

### Example Test Workflow

1. **Check Health**:

   - Go to "Utility" tab
   - Click "Health Check"
   - Should see status: ok

2. **Ingest an Artifact**:

   - Go to "Ingest Artifact" tab
   - Select type: "model"
   - Enter URL: `https://huggingface.co/bert-base-uncased`
   - Click "Ingest Artifact"
   - Note the returned ID

3. **List All Artifacts**:

   - Go to "List Artifacts" tab
   - Keep default query (name: "\*")
   - Click "List Artifacts"
   - Should see your ingested artifact

4. **Get Specific Artifact**:
   - Go to "Get Artifact" tab
   - Enter the artifact ID from step 2
   - Click "Get Artifact"

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`

- **Solution**: Activate virtual environment and install dependencies
  ```powershell
  .\.venv\Scripts\activate
  pip install -r requirements.txt
  ```

**Problem**: Backend won't start or shows port in use

- **Solution**: Kill process using port 8000 or use a different port
  ```powershell
  # Use different port
  python -m uvicorn bs.src.app:app --reload --port 8001
  # Update Frontend/.env to: VITE_API_BASE_URL=http://localhost:8001/api
  ```

**Problem**: Database errors

- **Solution**: The database is created automatically in `/tmp/registry.db` (or local path on Windows)
  - Try the reset endpoint: DELETE `/api/reset`

### Frontend Issues

**Problem**: `npm: command not found`

- **Solution**: Install Node.js from https://nodejs.org/

**Problem**: API calls fail with CORS errors

- **Solution**: Ensure backend is running and CORS is configured (already done in app.py)

**Problem**: Frontend shows "Error: Network Error"

- **Solution**:
  1. Check backend is running at `http://localhost:8000`
  2. Verify `.env` file exists in Frontend folder with: `VITE_API_BASE_URL=http://localhost:8000/api`
  3. Restart frontend dev server after changing .env

**Problem**: Environment variables not loading

- **Solution**: Restart the Vite dev server (Ctrl+C and run `npm run dev` again)

## Configuration Files

### Backend Configuration

- `.env` (root): Backend environment variables
- `bs/src/app.py`: Main FastAPI application
- `bs/src/models_db.py`: Database models and connection

### Frontend Configuration

- `Frontend/.env`: Frontend environment variables
  ```
  VITE_API_BASE_URL=http://localhost:8000/api
  ```
- `Frontend/src/services/apiClient.js`: Axios client configuration

## Available Endpoints

| Method | Endpoint                  | Description                    |
| ------ | ------------------------- | ------------------------------ |
| GET    | `/health`                 | Health check                   |
| GET    | `/tracks`                 | Get planned tracks             |
| DELETE | `/reset`                  | Reset system                   |
| POST   | `/artifacts`              | List artifacts by query        |
| POST   | `/artifact/{type}`        | Ingest new artifact            |
| POST   | `/artifact/byRegEx`       | Search by regex                |
| GET    | `/artifact/{type}/{id}`   | Get specific artifact          |
| GET    | `/artifact/byName/{name}` | Get artifact by name           |
| GET    | `/docs`                   | API documentation (Swagger UI) |

## Database

- **Type**: SQLite (local file-based)
- **Location**: `/tmp/registry.db` (or Windows temp equivalent)
- **Tables**: `artifacts` (id, name, type, description, url)
- **Reset**: Use DELETE `/reset` endpoint to clear all data

## Notes

- Backend runs on port **8000**
- Frontend runs on port **5173** (default Vite port)
- CORS is configured to allow `http://localhost:5173`
- The test page is at `/test` route (not the login page)
- All API requests are logged in the console panel on the test page
