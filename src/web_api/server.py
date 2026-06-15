"""
FastAPI Web Server for HFOrchestra CLI Commands
Provides REST API endpoints for all CLI functionality
"""

import asyncio
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import json as json_lib
from pydantic import BaseModel
import uvicorn

# Windows-specific imports for hiding console window
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

# Add src directory to path to import hforchestra modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import comprehensive flags configuration
try:
    # Try importing from same directory
    import importlib.util
    flags_config_path = Path(__file__).parent / "flags_config.py"
    if flags_config_path.exists():
        spec = importlib.util.spec_from_file_location("flags_config", flags_config_path)
        flags_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flags_config)
        ALL_FLAGS = flags_config.ALL_FLAGS
    else:
        ALL_FLAGS = {}
except Exception:
    # Fallback if flags_config not found
    ALL_FLAGS = {}

app = FastAPI(title="HFOrchestra Web API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary directory for uploaded files - Use absolute path based on server file location
# This ensures consistency regardless of where the server is started from
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Auth Configuration
ADMIN_PASSWORD = os.getenv("HFORCH_ADMIN_PASSWORD", "admin")
# Generate a random session token on startup
import uuid
SESSION_TOKEN = str(uuid.uuid4())
print(f"🔒 Admin password: {ADMIN_PASSWORD}")
print(f"🔑 Session token: {SESSION_TOKEN}")

# Store running processes for cancellation
running_processes = {}
process_counter = 0

def safe_print(*args, **kwargs):
    """Safely print to console handling Unicode encoding errors on Windows."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback for Windows consoles that can't handle emojis
        try:
            # Create a clean version of the message for console printing
            clean_args = []
            for arg in args:
                if isinstance(arg, str):
                    clean_args.append(arg.encode('ascii', 'replace').decode('ascii'))
                else:
                    clean_args.append(arg)
            print(*clean_args, **kwargs)
        except Exception:
            pass  # If even fallback fails, just suppress


class CommandRequest(BaseModel):
    """Request model for CLI command execution"""
    prompt: Optional[str] = None
    file_path: Optional[str] = None
    flags: Dict[str, Any] = {}
    task_type: Optional[str] = None


class LoginRequest(BaseModel):
    """Request model for login"""
    password: str


class CommandResponse(BaseModel):
    """Response model for CLI command execution"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: Optional[float] = None


def build_cli_command(args: Dict[str, Any], file_path: Optional[str] = None) -> List[str]:
    """
    Build CLI command from request parameters.
    Converts flags dictionary to command-line arguments dynamically.
    """
    # Use python module to call main.py directly
    src_dir = Path(__file__).parent.parent
    main_py = src_dir / "hforchestra" / "main.py"
    
    if main_py.exists():
        # Force unbuffered output with -u
        cmd = [sys.executable, "-u", str(main_py)]
    else:
        # Fallback to module approach, unbuffered
        cmd = [sys.executable, "-u", "-m", "hforchestra.main"]
    
    # Add prompt if provided
    if args.get("prompt"):
        cmd.extend(["--prompt", args["prompt"]])
    
    # Add task alias if provided
    if args.get("task"):
        cmd.extend(["--task", args["task"]])
    
    # Add file path if provided
    if file_path:
        cmd.extend(["--file", file_path])
    elif args.get("file_path"):
        cmd.extend(["--file", args["file_path"]])
    
    # Handle special flags first
    # Help flag can have values like "all", "plan", "cu", etc.
    help_processed = False
    if args.get("help") is not None:
        help_value = args.get("help")
        if help_value == "all" or help_value == "true" or help_value is True:
            cmd.append("--help")
            if help_value == "all":
                cmd.append("all")
            help_processed = True
        elif help_value == "" or help_value is False:
            # Just --help with no value
            cmd.append("--help")
            help_processed = True
        elif isinstance(help_value, str) and help_value:
            # --help with a specific value (e.g., "plan", "cu")
            cmd.extend(["--help", str(help_value)])
            help_processed = True
    
    # If help was processed and it's a simple help request, we might want to return early
    # But for cases like --help --plan where plan is also a flag, we continue
    # For now, we continue processing other flags
    
    # Process all flags dynamically based on ALL_FLAGS config
    if ALL_FLAGS:
        for category, flags_list in ALL_FLAGS.items():
            for flag_def in flags_list:
                flag_name = flag_def["name"].replace("--", "")
                flag_key = flag_name.replace("-", "_")
                flag_type = flag_def.get("type", "boolean")
                
                # Skip help flag as it's handled above
                if flag_key == "help":
                    continue
                
                # Skip prompt and file flags - they are handled explicitly above
                if flag_key in ("prompt", "file", "file_path"):
                    continue
                
                value = args.get(flag_key)
                
                if flag_type == "boolean":
                    if value is True:
                        cmd.append(f"--{flag_name}")
                elif flag_type in ["string", "float", "integer"]:
                    if value is not None and value != "":
                        cmd.extend([f"--{flag_name}", str(value)])
                elif flag_type == "select":
                    if value is not None and value != "":
                        # Validate against options if provided
                        options = flag_def.get("options", [])
                        if not options or str(value) in options:
                            cmd.extend([f"--{flag_name}", str(value)])
    
    # Also handle flags that might not be in ALL_FLAGS config
    additional_flags = [
        # System stats
        "decision_stats", "novel_ai_stats", "performance_stats", "cache_stats",
        "analytics_demo", "model_recommendations", "update", "restore",
        # Evaluation & Planning
        "score", "judge", "plan", 
        # System Control
        "delegation", "recursion", "real_options", "prompt_quality_scoring",
        # Configuration
        "use_openai", "gpu", "cpu", "debug",
        # HYDE
        "enable_hyde", "use_hyde", "hyde_variants", "demo_hyde",
        # Innovation System
        "workflow_optimization", "semantic_analysis", "temporal_tracking",
        "predictive_mode", "full",
        # Data Analysis
        "jupyter", "export_pdf", "data_analyst", "datanalyst", "datascience",
        # Text Tasks
        "text_classification", "token_classification", "question_answering",
        "text_generation", "summarization", "translation", "fill_mask",
        "text2text_generation", "language_detection", "grammar_correction",
        "paraphrase_generation", "causal_language_modeling", "zero_shot_classification",
        "feature_extraction", "sentence_similarity", "anonymization",
        "coreference_resolution", "sentiment", "question", "ner", "summary",
        # Security Tasks
        "spam_detection", "malware_text_detection", "phishing_detection",
        "pii_detection", "hate_speech_detection", "cyberbullying_detection",
        "fake_news_detection", "legal_judgment_classification",
        "contract_clause_classification", "case_outcome_prediction",
        # Domain Tasks
        "financial_ner", "legal_ner", "biomedical_ner", "chemical_reaction_ner",
        "financial_sentiment_analysis", "scientific_abstract_summarization",
        # Content Analysis
        "emotion_detection", "sarcasm_detection", "stance_detection",
        "bias_detection", "hallucination_detection", "reading_level_assessment",
        "generation_groundedness", "citation_intent_classification",
        # Code Tasks
        "code_vulnerability_detection", "code_summary_generation", "code_clone_detection",
        # PE Analysis
        "pe_header_extraction",
        # Image Tasks
        "image_classification", "object_detection", "image_segmentation",
        "visual_question_answering", "document_question_answering",
        "zero_shot_image_classification", "depth_estimation", "image_feature_extraction",
        # Audio Tasks
        "automatic_speech_recognition", "audio_classification", "voice_activity_detection",
        "emotion_recognition",
        # Video Tasks
        "video_classification",
        # Generation Tasks
        "text_to_speech", "text_to_image", "image_super_resolution",
        # Structured Data
        "table_question_answering", "feature_ranking"
    ]
    
    for flag in additional_flags:
        if args.get(flag, False) is True:
            cmd.append(f"--{flag.replace('_', '-')}")
    
    # Handle string flags that might have empty values or specific values
    string_flags_map = {
        "tasks": "--tasks",
        "model_ranking": "--model-ranking",
        "search_query": "--search-query",
        "top_k": "--top-k",
        "add_documents": "--add-documents",
        "config": "--config",
        "load_model": "--load-model",
        "api_keys": "--api-keys",
        "language": "--language",
        "budget": "--budget",
        "innovation_level": "--innovation-level",
        "selection_strategy": "--selection-strategy",
        "ml_ensemble_method": "--ml-ensemble-method",
        "ml_confidence_threshold": "--ml-confidence-threshold",
        "ml_cleanup": "--ml-cleanup",
        "sinq_nbits": "--sinq-nbits",
        "sinq_group_size": "--sinq-group-size",
        "sinq_tiling_mode": "--sinq-tiling-mode",
        "sinq_method": "--sinq-method"
    }
    
    for key, flag_name in string_flags_map.items():
        value = args.get(key)
        # Handle both boolean True (just flag) and string values
        if value is True:
            # Just add the flag without value (e.g., --tasks)
            cmd.append(flag_name)
        elif value is not None and value != "":
            # Add flag with value (e.g., --tasks audio)
            cmd.extend([flag_name, str(value)])
    
    # Additional fallback for flags that might not be in ALL_FLAGS
    # This ensures backward compatibility
    if not ALL_FLAGS:
        common_boolean_flags = [
            "chain_of_thought", "enable_ml", "use_openai", "verbose", "debug",
            "gpu", "cpu", "sinq", "enable_innovations", "enable_hyde", "use_hyde",
            "stats", "clearcache", "text_classification", "image_classification"
        ]
        
        for flag in common_boolean_flags:
            if args.get(flag, False) is True:
                cmd.append(f"--{flag.replace('_', '-')}")
        
        # Common value flags
        value_flags_map = {
            "budget": "--budget",
            "language": "--language",
            "selection_strategy": "--selection-strategy",
        }
        
        for key, flag_name in value_flags_map.items():
            value = args.get(key)
            if value is not None and value != "":
                cmd.extend([flag_name, str(value)])
    
    return cmd


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "HFOrchestra Web API",
        "version": "1.0.0",
        "description": "REST API for HFOrchestra CLI commands",
        "endpoints": {
            "/api/execute": "Execute CLI command",
            "/api/upload": "Upload file for processing",
            "/api/flags": "Get available CLI flags",
            "/api/help": "Get help for specific flag"
        }
    }


async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify the authorization token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    
    # Check for Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    
    token = authorization.split(" ")[1]
    if token != SESSION_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return True


@app.post("/api/login")
async def login(request: LoginRequest):
    """Login with password to get session token"""
    if request.password == ADMIN_PASSWORD:
        return {"success": True, "token": SESSION_TOKEN}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )


@app.get("/api/check-auth")
async def check_auth(authorized: bool = Depends(verify_token)):
    """Check if token is valid"""
    return {"authenticated": True}



@app.get("/api/flags")
async def get_flags():
    # Public endpoint - no auth required for initial loading
    """Get list of all available CLI flags"""
    try:
        # Use comprehensive flags configuration
        if ALL_FLAGS:
            return {"flags": ALL_FLAGS}
        else:
            # Fallback if flags_config not available
            return {
                "error": "Flags configuration not loaded",
                "flags": {
                    "basic": [
                        {"name": "--prompt", "type": "string", "description": "Prompt/question for processing"},
                        {"name": "--file", "type": "string", "description": "Input file path"},
                    ]
                }
            }
    except Exception as e:
        return {"error": str(e), "flags": {}}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), authorized: bool = Depends(verify_token)):
    """Upload a file for processing"""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": file.filename,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_command_output(cmd, process_id, start_time):
    """Generator function to stream command output in real-time"""
    import time
    try:
        # On Windows, use subprocess.Popen with CREATE_NO_WINDOW to prevent console window
        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            process_obj = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent),
                creationflags=CREATE_NO_WINDOW,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            # Store process for cancellation
            running_processes[process_id] = {
                'process': process_obj,
                'platform': 'windows',
                'start_time': start_time
            }
            
            # Read output line by line and yield immediately
            output_lines = []
            try:
                # Use asyncio to read stdout in a non-blocking way
                import queue
                import threading
                
                output_queue = queue.Queue()
                read_done = threading.Event()
                
                def read_stdout():
                    try:
                        for line in process_obj.stdout:
                            if process_id not in running_processes:
                                break
                            stripped = line.rstrip()
                            if stripped:
                                output_queue.put(stripped)
                        output_queue.put(None)  # Signal end
                    except Exception as e:
                        output_queue.put(f"⚠️ Read error: {str(e)}")
                        output_queue.put(None)
                    finally:
                        read_done.set()
                
                # Start reading in background thread
                reader_thread = threading.Thread(target=read_stdout, daemon=True)
                reader_thread.start()
                
                # Yield lines as they come
                while True:
                    try:
                        # Check if cancelled
                        if process_id not in running_processes:
                            process_obj.terminate()
                            yield f"data: {json_lib.dumps({'type': 'output', 'line': '⚠️ Process cancelled by user'}, ensure_ascii=False)}\n\n"
                            break
                        
                        # Try to get a line (non-blocking with timeout)
                        try:
                            line = output_queue.get(timeout=0.1)
                            if line is None:
                                # End of stream
                                break
                            output_lines.append(line)
                            # Print to server console
                            safe_print(line, flush=True)
                            # Stream to client immediately
                            yield f"data: {json_lib.dumps({'type': 'output', 'line': line}, ensure_ascii=False)}\n\n"
                        except queue.Empty:
                            # No data yet, check if process is still running
                            if process_obj.poll() is not None:
                                # Process ended, wait for remaining output
                                read_done.wait(timeout=1)
                                # Drain remaining queue
                                while True:
                                    try:
                                        line = output_queue.get_nowait()
                                        if line is None:
                                            break
                                        output_lines.append(line)
                                        safe_print(line, flush=True)
                                        yield f"data: {json_lib.dumps({'type': 'output', 'line': line}, ensure_ascii=False)}\n\n"
                                    except queue.Empty:
                                        break
                                break
                            # Continue waiting
                            await asyncio.sleep(0.05)  # Small delay to prevent busy-waiting
                            continue
                    except Exception as e:
                        if process_id in running_processes:
                            error_msg = f"⚠️ Process interrupted: {str(e)}"
                            yield f"data: {json_lib.dumps({'type': 'output', 'line': error_msg}, ensure_ascii=False)}\n\n"
                        break
            except Exception as e:
                if process_id in running_processes:
                    error_msg = f"⚠️ Process interrupted: {str(e)}"
                    yield f"data: {json_lib.dumps({'type': 'output', 'line': error_msg})}\n\n"
            
            # Wait for process to complete
            if process_id in running_processes:
                process_obj.wait()
                returncode = process_obj.returncode
            else:
                returncode = -1  # Cancelled
        else:
            # On Unix-like systems, use asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent)
            )
            
            # Store process for cancellation
            running_processes[process_id] = {
                'process': process,
                'platform': 'unix',
                'start_time': start_time
            }
            
            # Read output line by line and yield immediately
            output_lines = []
            try:
                while True:
                    # Check if process was cancelled
                    if process_id not in running_processes:
                        process.terminate()
                        yield f"data: {json_lib.dumps({'type': 'output', 'line': '⚠️ Process cancelled by user'})}\n\n"
                        break
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    if decoded_line:
                        output_lines.append(decoded_line)
                        # Print to server console
                        safe_print(decoded_line, flush=True)
                        # Stream to client immediately
                        yield f"data: {json_lib.dumps({'type': 'output', 'line': decoded_line}, ensure_ascii=False)}\n\n"
            except Exception as e:
                if process_id in running_processes:
                    error_msg = f"⚠️ Process interrupted: {str(e)}"
                    yield f"data: {json_lib.dumps({'type': 'output', 'line': error_msg})}\n\n"
            
            # Wait for process to complete
            if process_id in running_processes:
                await process.wait()
                returncode = process.returncode
            else:
                returncode = -1  # Cancelled
        
        execution_time = time.time() - start_time
        
        # Clean up process from running_processes
        if process_id in running_processes:
            del running_processes[process_id]
        
        # Intelligently detect errors from output even if returncode is 0
        error_message = None
        has_error = False
        
        # Combine output lines for error detection
        accumulated_output = '\n'.join(output_lines) if output_lines else ''
        
        # Check for error patterns in accumulated output
        error_patterns = [
            'Error:', 'ERROR:', 'Exception:', 'Traceback:',
            'Failed:', 'FAILED:', 'failed:', 'error:',
            '429 Client Error', 'Too Many Requests', 'rate limit',
            'Error populating', 'Error during population',
            'Max retries exceeded', 'Rate limit persists'
        ]
        
        # Check accumulated output for errors
        output_text = accumulated_output.lower() if accumulated_output else ''
        for pattern in error_patterns:
            if pattern.lower() in output_text:
                has_error = True
                # Extract the error line(s)
                error_lines = [line for line in output_lines if pattern.lower() in line.lower()]
                if error_lines:
                    error_message = '\n'.join(error_lines[-3:])  # Last 3 error lines
                break
        
        # Also check returncode
        if returncode == -1:
            error_message = "Process cancelled by user"
            has_error = True
        elif returncode != 0:
            if not error_message:
                error_message = f"Process exited with code {returncode}"
            has_error = True
        
        # Determine final success status
        final_success = returncode == 0 and not has_error
        
        # Send final status
        yield f"data: {json_lib.dumps({'type': 'complete', 'success': final_success, 'returncode': returncode, 'execution_time': execution_time, 'error': error_message}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        execution_time = time.time() - start_time
        # Clean up on error
        if 'process_id' in locals() and process_id in running_processes:
            try:
                proc_info = running_processes[process_id]
                if proc_info['platform'] == 'windows':
                    proc_info['process'].terminate()
                else:
                    proc_info['process'].terminate()
            except:
                pass
            del running_processes[process_id]
        yield f"data: {json_lib.dumps({'type': 'error', 'error': str(e), 'execution_time': execution_time})}\n\n"


@app.get("/api/execute-stream")
async def execute_command_stream(
    flags: str = "",
    prompt: Optional[str] = None,
    file_path: Optional[str] = None,
    authorized: bool = Depends(verify_token)
):
    """Execute CLI command with streaming output via Server-Sent Events"""

    import time
    import uuid
    start_time = time.time()
    
    # Generate unique process ID
    global process_counter
    process_counter += 1
    process_id = str(uuid.uuid4())
    
    try:
        # Parse flags from query string
        flags_dict = json.loads(flags) if flags else {}
        if prompt:
            flags_dict["prompt"] = prompt
        if file_path:
            flags_dict["file_path"] = file_path
        
        # DEBUG: Print exact flags being used
        safe_print(f"DEBUG: execute_command flags: {flags_dict}")
        if "prompt" in flags_dict:
             safe_print(f"DEBUG: execute_command prompt: '{flags_dict['prompt']}'")
        else:
             safe_print("DEBUG: execute_command prompt is MISSING from flags_dict")

        # Build command
        cmd = build_cli_command(flags_dict, file_path)
        
        # Log command execution start
        safe_print(f"\n{'='*60}", flush=True)
        safe_print(f"🚀 Executing command (streaming): {' '.join(cmd)}", flush=True)
        safe_print(f"{'='*60}", flush=True)
        
        # Return streaming response
        return StreamingResponse(
            stream_command_output(cmd, process_id, start_time),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        execution_time = time.time() - start_time
        async def error_stream():
            yield f"data: {json_lib.dumps({'type': 'error', 'error': str(e), 'execution_time': execution_time}, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )


@app.post("/api/execute")
async def execute_command(request: CommandRequest, authorized: bool = Depends(verify_token)):
    """Execute CLI command with provided parameters - streams output in real-time"""
    import time
    import uuid
    start_time = time.time()
    
    # Generate unique process ID
    global process_counter
    process_counter += 1
    process_id = str(uuid.uuid4())
    
    try:
        # CRITICAL FIX: Merge prompt and file_path into flags dict
        # build_cli_command expects args.get("prompt") to find the prompt
        flags_dict = dict(request.flags)  # Make a copy
        if request.prompt:
            flags_dict["prompt"] = request.prompt
        if request.file_path:
            flags_dict["file_path"] = request.file_path
        
        # Build command with merged flags
        cmd = build_cli_command(flags_dict, request.file_path)
        
        # Log command execution start
        safe_print(f"\n{'='*60}", flush=True)
        safe_print(f"🚀 Executing command: {' '.join(cmd)}", flush=True)
        safe_print(f"{'='*60}", flush=True)
        
        # Return streaming response
        return StreamingResponse(
            stream_command_output(cmd, process_id, start_time),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        execution_time = time.time() - start_time
        # Clean up process from running_processes on error
        if 'process_id' in locals() and process_id in running_processes:
            try:
                proc_info = running_processes[process_id]
                if proc_info['platform'] == 'windows':
                    proc_info['process'].terminate()
                else:
                    proc_info['process'].terminate()
            except:
                pass
            del running_processes[process_id]
        return CommandResponse(
            success=False,
            output="",
            error=str(e),
            execution_time=execution_time
        )


@app.post("/api/execute-with-file")
async def execute_with_file(
    file: Optional[UploadFile] = File(None),
    prompt: Optional[str] = Form(None),
    flags: Optional[str] = Form("{}"),
    authorized: bool = Depends(verify_token)
):
    """Execute command with file upload"""
    import time
    start_time = time.time()
    
    try:
        # Parse flags JSON
        flags_dict = json.loads(flags) if flags else {}
        
        # Handle file upload
        file_path = None
        if file:
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            flags_dict["file_path"] = str(file_path)
        
        if prompt:
            flags_dict["prompt"] = prompt
        
        # Build and execute command
        cmd = build_cli_command(flags_dict, file_path)
        
        # Log command execution start
        safe_print(f"\n{'='*60}", flush=True)
        safe_print(f"🚀 Executing command with file: {' '.join(cmd)}", flush=True)
        safe_print(f"{'='*60}", flush=True)
        
        # On Windows, use subprocess.Popen with CREATE_NO_WINDOW to prevent console window
        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            # Use encoding='utf-8' with errors='replace' to handle Unicode issues
            process_obj = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent),
                creationflags=CREATE_NO_WINDOW,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            # Read output line by line
            output_lines = []
            for line in process_obj.stdout:
                stripped = line.rstrip()
                if stripped:
                    output_lines.append(stripped)
                    # Also print to server console
                    safe_print(stripped, flush=True)
            
            # Wait for process to complete
            process_obj.wait()
            returncode = process_obj.returncode
        else:
            # On Unix-like systems, use asyncio normally
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent)
            )
            
            # Read output line by line to capture all logs
            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='replace').rstrip()
                if decoded_line:
                    output_lines.append(decoded_line)
                    # Also print to server console
                    safe_print(decoded_line, flush=True)
            
            # Wait for process to complete
            await process.wait()
            returncode = process.returncode
        
        execution_time = time.time() - start_time
        
        # Log completion
        safe_print(f"\n{'='*60}", flush=True)
        safe_print(f"✅ Command completed in {execution_time:.2f}s (exit code: {returncode})", flush=True)
        safe_print(f"{'='*60}\n", flush=True)
        
        # Combine all output
        output = '\n'.join(output_lines)
        
        # Extract error message from output if process failed
        error_message = None
        if returncode != 0:
            # Look for error patterns in the output
            error_patterns = [
                'Error:', 'ERROR:', 'Exception:', 'Traceback:',
                'Failed:', 'FAILED:', 'failed:', 'error:'
            ]
            error_lines = []
            for line in output_lines:
                if any(pattern in line for pattern in error_patterns):
                    error_lines.append(line)
            
            if error_lines:
                # Get the last few error lines for context
                error_message = '\n'.join(error_lines[-5:])
            else:
                # Fallback to generic message
                error_message = f"Process exited with code {returncode}"
        
        return CommandResponse(
            success=returncode == 0,
            output=output,
            error=error_message,
            execution_time=execution_time
        )
    except Exception as e:
        execution_time = time.time() - start_time
        # Clean up process from running_processes on error
        if 'process_id' in locals() and process_id in running_processes:
            try:
                proc_info = running_processes[process_id]
                if proc_info['platform'] == 'windows':
                    proc_info['process'].terminate()
                else:
                    proc_info['process'].terminate()
            except:
                pass
            del running_processes[process_id]
        return CommandResponse(
            success=False,
            output="",
            error=str(e),
            execution_time=execution_time
        )


@app.post("/api/cancel")
async def cancel_command():
    """Cancel all running processes"""
    try:
        cancelled_count = 0
        for process_id, proc_info in list(running_processes.items()):
            try:
                if proc_info['platform'] == 'windows':
                    # On Windows, terminate the process
                    proc_info['process'].terminate()
                    # Wait a bit, then kill if still running
                    try:
                        proc_info['process'].wait(timeout=2)
                    except:
                        proc_info['process'].kill()
                else:
                    # On Unix, terminate the process
                    proc_info['process'].terminate()
                    # Wait a bit, then kill if still running
                    try:
                        await asyncio.wait_for(proc_info['process'].wait(), timeout=2)
                    except:
                        proc_info['process'].kill()
                cancelled_count += 1
            except Exception as e:
                print(f"Error cancelling process {process_id}: {e}")
            finally:
                # Remove from running processes
                if process_id in running_processes:
                    del running_processes[process_id]
        
        return {"success": True, "cancelled": cancelled_count, "message": f"Cancelled {cancelled_count} process(es)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/help/{flag}")
async def get_help(flag: str):
    """Get help for a specific flag"""
    try:
        project_root = Path(__file__).parent.parent
        main_py = project_root / "src" / "hforchestra" / "main.py"
        
        if main_py.exists():
            cmd = [sys.executable, str(main_py), "--help", flag]
        else:
            cmd = [sys.executable, "-m", "hforchestra.main", "--help", flag]
        # Prepare subprocess creation flags for Windows to hide console window
        kwargs = {
            'stdout': asyncio.subprocess.PIPE,
            'stderr': asyncio.subprocess.STDOUT,  # Merge stderr into stdout
            'cwd': str(Path(__file__).parent.parent)
        }
        
        if sys.platform == "win32":
            # Hide console window on Windows using CREATE_NO_WINDOW
            # CREATE_NO_WINDOW = 0x08000000
            kwargs['creationflags'] = 0x08000000
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            **kwargs
        )
        
        # Read output line by line
        output_lines = []
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode('utf-8', errors='ignore').rstrip()
            if decoded_line:
                output_lines.append(decoded_line)
        
        await process.wait()
        help_text = '\n'.join(output_lines)
        return {"flag": flag, "help": help_text}
    except Exception as e:
        return {"flag": flag, "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

