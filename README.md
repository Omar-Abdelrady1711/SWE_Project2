# ACME Trustworthy Model Registry

A full-stack web application for evaluating, scoring, and managing machine learning models from HuggingFace.  The system provides trustworthiness metrics and ratings for ML artifacts (models, datasets, and code repositories).

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)

## 🎯 Overview

The ACME Trustworthy Model Registry provides:
- **Automated ML artifact evaluation** from HuggingFace URLs
- **Multi-dimensional scoring system** including: 
  - Bus factor score
  - Correctness score
  - Ramp-up score
  - Responsive maintainer score
  - License compatibility
  - Dataset and code quality metrics
- **Web-based dashboard** for browsing and managing artifacts
- **REST API** for programmatic access
- **Role-based access control** with admin and user roles

## 🏗️ Architecture

- **Frontend**: React (Vite) with React Router
- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLite (local) / DynamoDB (AWS)
- **Deployment**: AWS Lambda + API Gateway (via SAM)
- **Authentication**: JWT-based with role management

## ✨ Features

- **URL-based ingestion**:  Submit HuggingFace URLs for automatic analysis
- **Comprehensive scoring**:  Multi-metric evaluation of ML artifacts
- **User authentication**:  Secure login with JWT tokens
- **Admin dashboard**: User management and system oversight
- **Test debugging interface**: Built-in API testing tools
- **AWS deployment ready**: SAM template for serverless deployment

## 🔧 Prerequisites

### Local Development
- Python 3.11 or higher
- Node.js 16+ and npm
- Git

### AWS Deployment
- AWS CLI configured
- AWS SAM CLI
- AWS account with appropriate permissions

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Omar-Abdelrady1711/SWE_Project2.git
cd SWE_Project2
```

### 2. Backend Setup

```bash
# Install Python dependencies
./run install

# Or manually: 
pip install -U pip setuptools wheel
pip install -e . 
pip install -e ".[dev]"
```

### 3. Frontend Setup

```bash
cd Frontend
npm install
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Database (for local development)
DATABASE_URL=sqlite:///./backend. db

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=1  # 0=Silent, 1=Info, 2=Debug
LOG_FILE=app.log  # Optional: log to file

# AWS (for deployment only)
AWS_LAMBDA_EXEC=false  # Set to true when running on Lambda
ARTIFACTS_TABLE=your-artifacts-table-name
RATINGS_TABLE=your-ratings-table-name
```

### Default Credentials

For development, the system includes default users: 

- **Admin**: `admin` / `admin123`
- **User**: `user1` / `pass123`

**⚠️ Change these credentials in production!**

## 🚀 Deployment

### Local Development

#### Option 1: Using Helper Scripts (Windows)

```bash
# Start backend
start_backend.bat

# Start frontend (in another terminal)
start_frontend.bat
```

#### Option 2: Manual Start

**Backend:**
```bash
# From project root
uvicorn bs.src.app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
# From Frontend directory
cd Frontend
npm run dev
```

The application will be available at: 
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Docker Deployment

```bash
# Build the image
docker build -t acme-registry .

# Run the container
docker run -p 8000:8000 acme-registry
```

### AWS Deployment

```bash
# Build and deploy using SAM
sam build
sam deploy --guided

# Follow the prompts to configure: 
# - Stack name
# - AWS Region
# - Confirm changes before deploy
```

After deployment, SAM will output: 
- **ApiUrl**: Your API Gateway endpoint
- **ArtifactsTableName**: DynamoDB table for artifacts
- **RatingsTableName**: DynamoDB table for ratings

## 💻 Usage

### Web Interface

1. **Login**: Navigate to `/login` and use your credentials
2. **Dashboard**: View all registered artifacts at `/dashboard`
3. **Upload**:  Submit new HuggingFace URLs at `/upload`
4. **User Management**: (Admin only) Manage users at `/users`
5. **Test/Debug**: Access API testing tools at `/test`

### CLI Interface

Evaluate artifacts from a file of URLs:

```bash
# Run evaluation
./run URL_FILE.txt

# Example URL file format (one per line):
# https://huggingface.co/username/model-name
# https://huggingface.co/datasets/username/dataset-name
```

### API Usage

#### Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Returns: {"access_token": ".. .", "token_type": "bearer"}
```

#### Submit Artifact

```bash
curl -X POST http://localhost:8000/api/package \
  -H "X-Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "URL": "https://huggingface.co/username/model",
    "JSProgram": "optional-js-code"
  }'
```

#### Get All Artifacts

```bash
curl -X GET http://localhost:8000/api/artifacts \
  -H "X-Authorization: Bearer YOUR_TOKEN"
```

#### Get Artifact Rating

```bash
curl -X GET http://localhost:8000/api/package/{id}/rate \
  -H "X-Authorization: Bearer YOUR_TOKEN"
```

## 📚 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/login` | User authentication | No |
| POST | `/api/auth/register` | Create new user | No |
| GET | `/api/artifacts` | List all artifacts | Yes |
| POST | `/api/package` | Submit new artifact | Yes |
| GET | `/api/package/{id}` | Get artifact details | Yes |
| GET | `/api/package/{id}/rate` | Get artifact rating | Yes |
| DELETE | `/api/package/{id}` | Delete artifact | Yes |
| POST | `/api/reset` | Reset database | Yes (Admin) |

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests with coverage
./run test

# Output format:  "X/Y test cases passed.  Z% line coverage achieved."
```

### Test Requirements

- Minimum 80% line coverage required
- Tests located in `test/` directory
- Uses pytest with coverage reporting

### Manual API Testing

Use the built-in test interface at `/test` or tools like: 
- Postman
- curl
- httpie

## 📁 Project Structure

```
SWE_Project2/
├── Frontend/                 # React frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── services/        # API client
│   │   └── App.jsx          # Main app component
│   └── package.json
├── bs/src/                  # Backend source
│   ├── acemcli/            # CLI and scoring engine
│   │   ├── metrics/        # Metric implementations
│   │   ├── orchestrator. py # Score computation
│   │   └── cli.py          # CLI interface
│   ├── auth/               # Authentication module
│   ├── app.py              # FastAPI application
│   ├── models_db.py        # Database models
│   └── schemas.py          # Pydantic schemas
├── test/                    # Test suite
├── template. yaml           # AWS SAM template
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── run                    # Main execution script
└── README.md              # This file
```

## 🔍 Scoring Metrics

The system evaluates artifacts across multiple dimensions:

- **Bus Factor**: Team diversity and knowledge distribution
- **Correctness**: Code quality and testing
- **Ramp-up**:  Documentation and ease of onboarding
- **Responsive Maintainer**: Community engagement
- **License Score**: License compatibility and presence
- **Size Score**: Repository and artifact size metrics
- **Dataset & Code Score**: Quality of associated datasets and code

Each metric ranges from 0.0 to 1.0, with higher scores indicating better quality. 

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
- Ensure Python 3.11+ is installed:  `python --version`
- Install dependencies: `./run install`
- Check port 8000 is available

**Frontend build fails:**
- Clear node_modules:  `rm -rf Frontend/node_modules`
- Reinstall: `cd Frontend && npm install`
- Check Node version: `node --version` (requires 16+)

**Database errors:**
- Delete `backend.db` and restart to reset
- Or use API:  `curl -X POST http://localhost:8000/api/reset`

**Authentication issues:**
- Verify JWT_SECRET_KEY is set
- Check token expiration settings
- Clear browser localStorage and re-login

## 📄 License

This project is part of an academic software engineering course. 

## 👥 Contributors

Omar Abdelrady and team

---

For additional documentation, see: 
- [TESTING_SETUP_GUIDE.md](TESTING_SETUP_GUIDE.md) - Detailed testing instructions
- [DYNAMODB_REVERSION. md](DYNAMODB_REVERSION.md) - DynamoDB implementation details
