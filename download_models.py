import os
import sys
import logging
import requests

from app.config import OLLAMA_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def check_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        response = requests.get("http://localhost:11434/", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def pull_ollama_model():
    """Tells the local Ollama instance to pull the required model."""
    logger.info(f"Preparing to pull Ollama model: {OLLAMA_MODEL}")
    
    if not check_ollama_running():
        logger.error("Ollama is not running. Please start Ollama first.")
        logger.error("You can download it from https://ollama.com/")
        sys.exit(1)

    # Use streaming request to show progress
    try:
        response = requests.post(
            "http://localhost:11434/api/pull",
            json={"name": OLLAMA_MODEL},
            stream=True
        )
        response.raise_for_status()

        logger.info(f"Downloading model {OLLAMA_MODEL}... this may take a while depending on your internet connection.")
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                if '"status"' in data:
                    # Very simple progress logger
                    import json
                    try:
                        msg = json.loads(data)
                        status = msg.get("status", "")
                        if "downloading" in status.lower() and "completed" in msg and "total" in msg:
                            completed = msg["completed"]
                            total = msg["total"]
                            percent = (completed / total) * 100
                            # Overwrite the same line in terminal
                            sys.stdout.write(f"\rProgress: {percent:.1f}% ({completed}/{total} bytes)")
                            sys.stdout.flush()
                        else:
                            sys.stdout.write(f"\r{status}\n")
                            sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass
        
        print("\n")
        logger.info(f"✓ Model {OLLAMA_MODEL} successfully pulled into Ollama!")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to pull model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Initializing models...")
    pull_ollama_model()
    logger.info("Done.")
