# Quick Start Guide - HFOrchestra Web Interface

## Prerequisites

- Python 3.9+
- Node.js 16+ and npm
- All HFOrchestra dependencies installed

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install FastAPI, uvicorn, and other required packages.

### 2. Install Node.js Dependencies

```bash
cd web_ui
npm install
```

### 3. Start the Servers

**Option A: Start Both Backend and Frontend Together (Recommended)**
```bash
python start_web_full.py
```
This will start both the backend API (port 8000) and frontend UI (port 3000) in one command.

**Option B: Start Separately**

**Backend Server:**

*Windows:*
```bash
start_web_server.bat
```
or
```bash
python start_web_server.py
```

*Linux/Mac:*
```bash
chmod +x start_web_server.sh
./start_web_server.sh
```

Or manually:
```bash
python -m uvicorn web_api.server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

**Frontend (in a new terminal):**

*Windows:*
```bash
start_web_ui.bat
```
or
```bash
python start_web_ui.py
```

*Linux/Mac:*
```bash
chmod +x start_web_ui.sh
./start_web_ui.sh
```

Or manually:
```bash
cd web_ui
npm run dev
```

The web interface will be available at `http://localhost:3000`

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Enter a prompt or question in the text area
3. Optionally upload a file
4. Select flags from the different tabs (Basic, Text Tasks, Image Tasks, etc.)
5. Click "Execute Command"
6. View the results in the result panel

## Example Commands

### Text Classification
- Prompt: "I love this product!"
- Flag: `--text-classification`

### Image Analysis
- Upload: An image file
- Prompt: "What is in this image?"
- Flag: `--image-classification`

### File Analysis
- Upload: A document file
- Prompt: "Summarize this document"
- Flag: `--summarization`

### System Statistics
- Flag: `--stats` (no prompt needed)

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Ensure all Python dependencies are installed
- Check that `src/hforchestra/main.py` exists

### Frontend won't start
- Check if port 3000 is available
- Ensure Node.js dependencies are installed (`npm install`)
- Check browser console for errors

### Commands not executing
- Check backend logs for errors
- Ensure the CLI module is properly installed
- Verify file paths are correct

### CORS Errors
- Ensure backend is running on port 8000
- Check that CORS middleware is enabled in `web_api/server.py`

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Next Steps

- Read `README_WEB_INTERFACE.md` for detailed documentation
- Explore all available flags in the web UI
- Check the API endpoints for programmatic access

