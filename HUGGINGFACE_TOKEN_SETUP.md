# HuggingFace API Token Setup

## Problem
You're encountering this error when running ensemble models:
```
HuggingFace Inference API failed: HuggingFace API key not found. Set HUGGINGFACE_API_KEY environment variable.
```

## Solution
The HFOrchestra system needs a HuggingFace API token to access models for ensemble processing. Here are several ways to set it up:

## Method 1: Interactive Python Script (Recommended)
```bash
python setup_hf_token.py
```
This will:
- Guide you through the setup process
- Create a `.env` file with your token
- Set both `HUGGINGFACE_API_KEY` and `HF_TOKEN` variables

## Method 2: Windows Batch File
```cmd
set_hf_token.bat
```
This will set the token for your current command prompt session.

## Method 3: PowerShell Script
```powershell
.\set_hf_token.ps1
```
This will set the token for your current PowerShell session.

## Method 4: Manual Environment Variable Setup

### Windows (Command Prompt)
```cmd
set HUGGINGFACE_API_KEY=your_token_here
set HF_TOKEN=your_token_here
```

### Windows (PowerShell)
```powershell
$env:HUGGINGFACE_API_KEY = "your_token_here"
$env:HF_TOKEN = "your_token_here"
```

### Windows (System Environment Variables)
1. Open System Properties → Advanced → Environment Variables
2. Add new User Variable:
   - Variable name: `HUGGINGFACE_API_KEY`
   - Variable value: `your_token_here`
3. Add another User Variable:
   - Variable name: `HF_TOKEN`
   - Variable value: `your_token_here`

### Linux/macOS
```bash
export HUGGINGFACE_API_KEY=your_token_here
export HF_TOKEN=your_token_here
```

## Method 5: .env File
Create a `.env` file in the project root:
```
HUGGINGFACE_API_KEY=your_token_here
HF_TOKEN=your_token_here
```

## Getting Your HuggingFace Token
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Give it a name (e.g., "HFOrchestra")
4. Select "Read" permissions
5. Copy the generated token

## Verification
After setting up your token, you can verify it's working:
```bash
python setup_hf_token.py --check
```

## What Was Fixed
- **Inconsistency**: The system now checks for both `HUGGINGFACE_API_KEY` and `HF_TOKEN` environment variables
- **Better Error Messages**: More helpful error messages that mention both variable names
- **Automatic Loading**: The main.py file now automatically loads `.env` files
- **Setup Tools**: Multiple convenient ways to set up your token

## Ensemble Models
Once your token is set up, you can run ensemble commands like:
```bash
python main.py --enable-ml --text-generation --prompt 'List three colors'
```

The system will now be able to:
- ✅ Access HuggingFace models
- ✅ Run multiple models in parallel
- ✅ Combine their outputs
- ✅ Provide cost and performance metrics
