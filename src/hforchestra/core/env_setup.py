
import os
import json

def setup_environment():
    """
    Reads langextract config and removes Gemini environment variables if specified.
    This must be called before any module that might import langextract.
    """
    try:
        # Construct the path relative to this file's location.
        # __file__ -> core/env_setup.py
        # os.path.dirname(__file__) -> core/
        # os.path.join(..., '..', 'config', 'langextract_config.json') -> config/langextract_config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'langextract_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                lx_cfg = json.load(f)

            if lx_cfg.get("disable_gemini"):
                gemini_keys = ("GOOGLE_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
                for key in gemini_keys:
                    if key in os.environ:
                        os.environ.pop(key, None)
                        if 'HFORCH_DEBUG' in os.environ:
                            print(f"[DEBUG] core.env_setup: Stripped '{key}' from environment.")
    except Exception as e:
        if 'HFORCH_DEBUG' in os.environ:
            print(f"[DEBUG] core.env_setup: Could not process langextract config to disable Gemini: {e}")

# Run the setup immediately when this module is imported.
setup_environment()
