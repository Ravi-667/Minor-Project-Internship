
# 🧠 Synapse: The Offline AI Study & Dev Companion

**Synapse** is a privacy-first, fully local AI assistant designed for students, developers, and researchers. Unlike cloud-based tools, Synapse runs entirely on your machine (`localhost`), utilizing Retrieval-Augmented Generation (RAG) to chat with your personal files and a Semantic Router to switch between Study, Developer, and Research modes automatically.

-----

## ✨ Key Features

  * **🔒 100% Offline & Private:** No data leaves your machine. Powered by local LLMs (DeepSeek, Qwen) via Ollama.
  * **📚 RAG (Chat with Docs):** Ingest PDFs, DOCX, and text files into a local Vector Database (Qdrant) to get citation-backed answers.
  * **🧠 Intelligent Routing:** A Semantic Router analyzes your intent to dynamically switch tools:
      * **Study Mode:** Explains concepts and generates syllabi.
      * **Developer Mode:** Writes Python code with file-system access.
      * **Quiz Mode:** Generates active-recall questions from your notes.
      * **Research Mode:** Deep retrieval from local docs or external APIs.
  * **💾 Long-Term Memory:** Uses **Mem0** to remember your preferences, project details, and learning progress across restarts.
  * **⚡ One-Click Launch:** A single script handles Docker, dependencies, ingestion, and server startup.

-----

## 🛠️ Architecture

The system follows a micro-service architecture running locally:

1.  **Frontend:** Vanilla JS + Tailwind CSS (served statically, no internet needed).
2.  **Backend:** FastAPI (Python) handling async websocket/streaming.
3.  **Brain:** Ollama running `deepseek-r1:7b` (Reasoning) and `qwen2.5-coder` (Coding).
4.  **Memory:** Qdrant (Vector DB in Docker) + SQLite (Chat Logs).

-----

## 🚀 Getting Started

### Prerequisites

1.  **Docker Desktop** (Required for the Qdrant database).
2.  **Python 3.10+**.
3.  **Ollama** (Download from [ollama.com](https://ollama.com)).

### 1\. Setup Models

Pull the required quantized models to your machine:

```bash
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text:v1.5
```

### 2\. Clone & Configure

Clone the repository and set up your environment variables.

```bash
git clone https://github.com/yourusername/synapse.git
cd synapse
```

Create a `.env` file in the root directory:

```ini
# .env file
LINKUP_API_KEY=your_key_here  # Optional: For Research Mode
MEM0_TELEMETRY=false
```

### 3\. Install Dependencies

We recommend using `uv` for fast syncing, but pip works too.

```bash
pip install uv
uv sync
# OR standard pip:
# pip install -r requirements.txt
```

-----

## 🏃‍♂️ How to Run

We have streamlined the startup process into a single **Master Script**.

```bash
python launcher.py
```

**What this script does:**

1.  🐳 Checks if Docker is running (starts Qdrant container).
2.  📦 Syncs Python dependencies via `uv`.
3.  📄 Runs `ingest.py` to index any new files in the `/data` folder.
4.  🔥 Starts the FastAPI server and opens your browser.

-----

## 📂 Project Structure

```text
synapse/
├── agent.py            # Core Logic: Semantic Router & LLM Chains
├── server.py           # FastAPI Backend & Endpoints
├── ingest.py           # RAG Pipeline: Chunking & Embedding
├── memory.py           # SQLite Database for Chat History
├── launcher.py         # Master Startup Script
├── run.py              # CLI Menu (Alternative to launcher)
├── docker-compose.yml  # Qdrant Database Config
├── pyproject.toml      # Dependency Management
├── data/               # 📂 PUT YOUR PDFs/DOCS HERE
├── static/             # Offline Frontend Assets (JS/CSS)
└── templates/          # HTML Interface
```

-----

## 🎮 Modes Explained

### 🎓 Study Mode

  * **Trigger:** "Teach me about transformers", "Create a syllabus for Calculus".
  * **Behavior:** Acts as a Socratic tutor. Uses RAG to explain concepts based on your uploaded notes.

### 💻 Developer Mode

  * **Trigger:** "Write a Python script for snake game", "Debug this error".
  * **Behavior:** Switches to `qwen2.5-coder`. Can write code blocks with syntax highlighting and save files to disk.

### 📝 Quiz Mode

  * **Trigger:** "Quiz me on Chapter 1", "Test my knowledge of Python".
  * **Behavior:** Enters a loop generating multiple-choice questions. Tracks score and gives feedback.

### 🔍 Research Mode

  * **Trigger:** "Search for recent AI papers", "Investigate deep learning trends".
  * **Behavior:** Uses Linkup API (if enabled) or deep local search to synthesize comprehensive reports.

-----

## 🔧 Troubleshooting

  * **"Connection Refused"**: Ensure Docker is running (`docker ps` should show qdrant).
  * **"Model not found"**: Run `ollama list` to check if you pulled `deepseek-r1:7b`.
  * **Ingestion Errors**: Ensure your PDFs in `/data` are not corrupted.

-----

## 📜 License

MIT License. Free to use and modify.
