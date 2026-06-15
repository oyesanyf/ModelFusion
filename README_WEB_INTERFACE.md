# HFOrchestra Web Interface

A modern web interface for executing HFOrchestra CLI commands through a REST API.

## Features

- 🚀 **Full CLI Access**: Execute all CLI commands through the web interface
- 📁 **File Upload**: Upload files for processing (supports 100+ file types)
- ⚙️ **Flag Management**: Configure all CLI flags through an intuitive UI
- 📊 **Real-time Results**: View command execution results in real-time
- 🎨 **Modern UI**: Beautiful, responsive React interface

## Architecture

### Backend (FastAPI)
- **Location**: `web_api/server.py`
- **Port**: 8000
- **Endpoints**:
  - `GET /` - API information
  - `GET /api/flags` - Get available CLI flags
  - `POST /api/upload` - Upload files
  - `POST /api/execute` - Execute CLI commands
  - `POST /api/execute-with-file` - Execute with file upload
  - `GET /api/help/{flag}` - Get help for specific flag

### Frontend (React + Vite)
- **Location**: `web_ui/`
- **Port**: 3000
- **Framework**: React 18 with Vite

## Installation

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Start the FastAPI server:
```bash
cd web_api
python server.py
```

Or using uvicorn directly:
```bash
uvicorn web_api.server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Install Node.js dependencies:
```bash
cd web_ui
npm install
```

2. Start the development server:
```bash
npm run dev
```

The web interface will be available at `http://localhost:3000`

## Usage

1. **Start Backend**: Run the FastAPI server (port 8000)
2. **Start Frontend**: Run the React dev server (port 3000)
3. **Open Browser**: Navigate to `http://localhost:3000`
4. **Execute Commands**:
   - Enter a prompt or question
   - Optionally upload a file
   - Select desired flags from the tabs
   - Click "Execute Command"
   - View results in the result panel

## API Examples

### Execute a simple command:
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is machine learning?",
    "flags": {
      "verbose": true,
      "chain_of_thought": true
    }
  }'
```

### Upload and process a file:
```bash
curl -X POST http://localhost:8000/api/execute-with-file \
  -F "file=@image.jpg" \
  -F "prompt=What is in this image?" \
  -F 'flags={"image_classification": true}'
```

## Supported Flags

All CLI flags are supported, including:

- **Basic**: `--prompt`, `--file`, `--budget`, `--verbose`, `--language`
- **Text Tasks**: `--text-classification`, `--text-generation`, `--summarization`, etc.
- **Image Tasks**: `--image-classification`, `--object-detection`, etc.
- **Audio Tasks**: `--automatic-speech-recognition`, `--audio-classification`, etc.
- **System**: `--stats`, `--tasks`, `--clearcache`, etc.
- **Advanced**: `--sinq`, `--enable-ml`, `--chain-of-thought`, etc.

## File Structure

```
HFOrchestra/
├── web_api/
│   ├── server.py          # FastAPI backend server
│   ├── uploads/           # Uploaded files directory
│   └── .gitignore
├── web_ui/
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   ├── App.css        # Styles
│   │   ├── main.jsx       # React entry point
│   │   └── index.css      # Global styles
│   ├── index.html         # HTML template
│   ├── vite.config.js     # Vite configuration
│   ├── package.json       # Node.js dependencies
│   └── .gitignore
└── README_WEB_INTERFACE.md
```

## Development

### Backend Development
- The FastAPI server uses hot-reload when run with `--reload` flag
- API documentation available at `http://localhost:8000/docs`

### Frontend Development
- React hot-reload is enabled in development mode
- Uses Vite for fast builds and HMR

## Production Deployment

### Build Frontend:
```bash
cd web_ui
npm run build
```

### Serve Frontend:
The built files will be in `web_ui/dist/`. Serve them with a static file server or configure the backend to serve them.

### Environment Variables:
Create a `.env` file in the project root for configuration:
```
API_HOST=0.0.0.0
API_PORT=8000
UPLOAD_DIR=web_api/uploads
```

## Troubleshooting

1. **CORS Errors**: Ensure the backend CORS settings include your frontend URL
2. **File Upload Issues**: Check that `web_api/uploads/` directory exists and is writable
3. **Command Execution Errors**: Check backend logs for detailed error messages
4. **Port Conflicts**: Change ports in `vite.config.js` (frontend) and `server.py` (backend)

## License

Same as HFOrchestra project.

