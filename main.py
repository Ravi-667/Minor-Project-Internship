import subprocess
import sys
import time
import os
import urllib.request

def run_step(command, step_name):
    """Runs a command and handles errors."""
    print(f"\n🚀 [STEP] {step_name}...")
    try:
        # If command is a string, shell=True. If list, shell=False.
        use_shell = isinstance(command, str)
        subprocess.run(command, shell=use_shell, check=True)
        print(f"✅ {step_name} Success.")
    except subprocess.CalledProcessError:
        print(f"❌ {step_name} Failed! Please check the error above.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Command not found. Is {command[0]} installed?")
        sys.exit(1)

def setup_offline_assets():
    """Ensures static assets (JS/CSS) are downloaded for offline use."""
    # Fast check: Only runs if 'static' folder is missing specific files
    static_dir = "static"
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    assets = {
        "tailwind.js": "https://cdn.tailwindcss.com",
        "marked.min.js": "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
        "highlight.min.css": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css",
        "highlight.min.js": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js",
        "mathjax.js": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
    }

    # Only checking for missing files (instant operation)
    missing_files = [f for f in assets if not os.path.exists(os.path.join(static_dir, f))]
    
    if missing_files:
        print(f"\n⬇️  Downloading {len(missing_files)} missing assets for offline mode...")
        for filename, url in assets.items():
            if filename in missing_files:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(os.path.join(static_dir, filename), 'wb') as out_file:
                        out_file.write(response.read())
                    print(f"   - Downloaded {filename}")
                except Exception as e:
                    print(f"   ⚠️ Failed to download {filename}: {e}")
        print("✅ Offline Assets Ready.")

def main():
    print("="*50)
    print("      🧠 SYNAPSE - FAST LAUNCHER")
    print("="*50)

    # --- 1. START DOCKER (Database) ---
    # Will skip automatically if containers are already running
    run_step(["docker-compose", "up", "-d"], "Starting Qdrant Database")

    # --- 2. SETUP OFFLINE ASSETS (Frontend) ---
    setup_offline_assets()

    # --- 3. INGEST DOCUMENTS (RAG Data) ---
    # Scans ./data folder and updates vector DB
    run_step([sys.executable, "ingest.py"], "Ingesting Knowledge Base")

    # --- 4. START SERVER (Application) ---
    print("\n🔥 Starting Web Server...")
    print("👉 Press Ctrl+C to stop Synapse.")
    print("-" * 50)
    
    # Auto-open browser
    try:
        url = "http://localhost:8000"
        if sys.platform == 'win32':
            subprocess.Popen(["start", url], shell=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except:
        pass 

    # Run Server
    subprocess.run([sys.executable, "server.py"])

if __name__ == "__main__":
    main()