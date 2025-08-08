# Collab Whiteboard Backend

A real-time collaborative whiteboard and chat backend built with FastAPI, featuring WebSocket support, Google Cloud Firestore, and Google Cloud Storage.

---

> ⚠️ **Disclaimer**  
> This project is **not intended for production use by companies**.
>
> It must contain security breaches
>  
> The main purpose of this repository is **educational**, focused on:
> - Python with FastAPI and Google Cloud
> - Google Cloud Firestore and Cloud Storage

---

## Features

- **Real-time Communication**: WebSocket-based chat and whiteboard collaboration
- **Multi-user Support**: Multiple users can draw and chat simultaneously
- **File Sharing**: Upload and share files in chat rooms
- **Google Cloud Integration**: Firestore for data storage, Cloud Storage for files
- **RESTful API**: Complete REST API for all operations
- **CORS Support**: Configured for frontend integration

## Technology Stack

- **Framework**: FastAPI
- **Database**: Google Cloud Firestore
- **File Storage**: Google Cloud Storage
- **Real-time**: WebSocket connections
- **Deployment**: Google Cloud Run
- **Language**: Python 3.11

## Project Structure

```
app/
├── __init__.py
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── models/                 # Data models
│   ├── __init__.py
│   ├── user.py
│   ├── chat.py
│   ├── whiteboard.py
│   └── file.py
├── api/                    # API routes
│   ├── __init__.py
│   ├── users.py
│   ├── chat.py
│   ├── whiteboard.py
│   └── files.py
├── services/               # Business logic
│   ├── __init__.py
│   ├── firestore_service.py
│   ├── storage_service.py
│   └── websocket_service.py
└── utils/                  # Utilities
    ├── __init__.py
    ├── auth.py
    └── helpers.py
```

## Setup Instructions

### Prerequisites

1. **Google Cloud Project**: Create a Google Cloud project
2. **Google Cloud CLI**: Install and authenticate with `gcloud auth application-default login`
3. **Python 3.11+**: Install Python 3.11 or higher
4. **Docker**: For containerized deployment

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd collab-whiteboard-backend
   ```

2. **Authenticate with Google Cloud**
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your Google Cloud settings
   ```

6. **Configure Google Cloud**
   - Set up Firestore database
   - Create Cloud Storage bucket

7. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# FastAPI Settings
DEBUG=false
HOST=0.0.0.0
PORT=8000

# CORS Settings
ALLOWED_ORIGINS=["http://localhost:3000", "https://your-frontend-domain.vercel.app"]

# Google Cloud Settings
GOOGLE_PROJECT_ID=your-google-cloud-project-id

# Cloud Storage Settings
STORAGE_BUCKET_NAME=YOUR_BUCKET_NAME
STORAGE_BUCKET_URL=https://storage.googleapis.com/YOUR_BUCKET_NAME

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB in bytes
```

## API Endpoints

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{user_id}` - Get user by ID
- `GET /api/v1/users/username/{username}` - Get user by username
- `PUT /api/v1/users/{user_id}/presence` - Update user presence

### Chat
- `POST /api/v1/chat/rooms/` - Create room
- `GET /api/v1/chat/rooms/` - Get active rooms
- `GET /api/v1/chat/rooms/{room_id}` - Get room by ID
- `GET /api/v1/chat/rooms/{room_id}/messages` - Get room messages
- `POST /api/v1/chat/rooms/{room_id}/messages` - Create message

### Whiteboard
- `GET /api/v1/whiteboard/rooms/{room_id}/state` - Get whiteboard state
- `POST /api/v1/whiteboard/rooms/{room_id}/actions` - Save whiteboard action
- `DELETE /api/v1/whiteboard/rooms/{room_id}/clear` - Clear whiteboard

### Files
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files/rooms/{room_id}/files` - Get room files
- `GET /api/v1/files/{file_id}/download` - Get file download URL
- `DELETE /api/v1/files/{file_id}` - Delete file

### WebSocket
- `WS /ws/{room_id}/{user_id}` - Real-time communication

## WebSocket Message Types

### Chat Messages
```json
{
  "type": "chat_message",
  "content": "Hello world!",
  "message_type": "text"
}
```

### Whiteboard Actions
```json
{
  "type": "whiteboard_action",
  "action_type": "draw",
  "x": 100.5,
  "y": 200.3,
  "color": "#FF0000",
  "brush_size": 2,
  "is_drawing": true
}
```

### File Uploads
```json
{
  "type": "file_upload",
  "file_id": "uuid",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 1024,
  "download_url": "https://..."
}
```

## Deployment to Google Cloud Run



### 1. Build and Push Docker Image

```bash
# Build the image
docker build -t us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/VERSION .

# Push to Artifact Registry
docker push us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/VERSION
```

**Example with specific version:**
```bash
docker build -t us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/0.0.10 .
docker push us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/0.0.10
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy collab-whiteboard-backend \
  --image us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/VERSION \
  --platform managed \
  --port 8000 \
  --timeout 3600 \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_PROJECT_ID=YOUR_PROJECT_ID,STORAGE_BUCKET_NAME=YOUR_BUCKET_NAME,STORAGE_BUCKET_URL=https://storage.googleapis.com/YOUR_BUCKET_NAME,DEBUG=true,MAX_FILE_SIZE=10485760 \
  --service-account=YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**Complete example:**
```bash
gcloud run deploy collab-whiteboard-backend \
  --image us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/0.0.10 \
  --platform managed \
  --port 8000 \
  --timeout 3600 \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_PROJECT_ID=YOUR_PROJECT_ID,STORAGE_BUCKET_NAME=collab-whiteboard-files,STORAGE_BUCKET_URL=https://storage.googleapis.com/collab-whiteboard-files,DEBUG=true,MAX_FILE_SIZE=10485760 \
  --service-account=collab-whiteboard-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Versioning

It's recommended to use semantic versioning for your Docker images:

```bash
# For a new version
VERSION=0.0.11
docker build -t us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/$VERSION .
docker push us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/$VERSION

# Deploy the new version
gcloud run deploy collab-whiteboard-backend \
  --image us-east1-docker.pkg.dev/YOUR_PROJECT_ID/collab-whiteboard-backend/$VERSION \
  # ... other options
```

### 4. Set Environment Variables

In Google Cloud Console:
1. Go to Cloud Run service
2. Edit and configure environment variables
3. Cloud Run will automatically use the default service account credentials

## Google Cloud Setup

### 1. Enable APIs
```bash
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 2. Create Firestore Database
```bash
gcloud firestore databases create --project=YOUR_PROJECT_ID
```

### 3. Create Artifact Registry Repository
```bash
# Create repository for Docker images
gcloud artifacts repositories create collab-whiteboard-backend \
  --repository-format=docker \
  --location=us-east1 \
  --description="Docker repository for Collab Whiteboard Backend"
```

### 4. Create Storage Bucket
```bash
gsutil mb gs://YOUR_BUCKET_NAME
gsutil iam ch allUsers:objectViewer gs://YOUR_BUCKET_NAME  #This will make your bucket public so do not share sensetive data
```

### 5. Service Account Permissions
For local development, ensure your authenticated account has:
- Firestore User
- Storage Object Admin

For Cloud Run deployment, the default service account will automatically have the necessary permissions.

### 6. Configure Docker Authentication
```bash
# Configure Docker to authenticate with Artifact Registry
gcloud auth configure-docker us-east1-docker.pkg.dev
```

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Formatting
```bash
pip install black isort
black .
isort .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
