import os
import urllib.request

# Define the folder for offline assets
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Dictionary of assets to download
assets = {
    "tailwind.js": "https://cdn.tailwindcss.com",
    "marked.min.js": "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
    "highlight.min.css": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css",
    "highlight.min.js": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js",
    # Note: MathJax is complex to fully offline due to dynamic font loading. 
    # This downloads the main script, but complex math might still require a full local build.
    "mathjax.js": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
}

print(f"⬇️  Downloading assets to '{STATIC_DIR}/'...")

for filename, url in assets.items():
    file_path = os.path.join(STATIC_DIR, filename)
    try:
        print(f"   Fetching {filename}...")
        # User-agent header is sometimes required by CDNs
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")

print("\n✅ Download complete! You can now run the offline server.")