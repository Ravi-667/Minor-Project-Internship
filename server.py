import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Import the new clear function
from memory import clear_db 

# Load Environment Variables
load_dotenv()

# --- LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

# --- GLOBAL STATE ---
ai_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ai_agent
    logger.info("🚀 Server starting...")
    
    # --- 1. RESET DB ON STARTUP ---
    clear_db() 
    
    try:
        from agent import WebAgent
        ai_agent = WebAgent()
        logger.info("✅ AI Agent online.")
    except Exception as e:
        logger.critical(f"❌ Failed to load AI Agent: {e}")
    yield
    logger.info("🛑 Server shutting down...")

app = FastAPI(lifespan=lifespan)

# --- MOUNT STATIC FILES ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, 
    allow_methods=["*"], allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    image_data: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    if not ai_agent:
        return {"status": "loading", "mode": "initializing...", "quiz_score": 0, "quiz_count": 0}
    return {
        "status": "active",
        "mode": ai_agent.mode,
        "current_quiz": ai_agent.quiz_data.get("topic"),
        "quiz_score": ai_agent.quiz_data.get("score", 0),
        "quiz_count": ai_agent.quiz_data.get("count", 0)
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not ai_agent:
        raise HTTPException(status_code=503, detail="System is initializing. Please wait.")
    
    return StreamingResponse(
        ai_agent.get_response(request.query, request.image_data),
        media_type="text/plain"
    )

@app.post("/reset")
async def reset_mode():
    if ai_agent:
        # --- 2. RESET DB ON BUTTON CLICK ---
        clear_db() 
        
        ai_agent.mode = "chat"
        ai_agent.quiz_data = {"topic": None, "question": None, "score": 0, "count": 0}
        
        # Also clear Mem0 short-term memory if needed
        # ai_agent.user_memory.reset() (Depends on Mem0 version)
        
        return {"status": "ok", "message": "Memory & Database Wiped."}
    return {"status": "not_ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)