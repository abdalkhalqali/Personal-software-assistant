"""
CodeCraft — AI Coding Agent (100% Free, Local)
Runs entirely on Hugging Face Docker Space (16GB RAM, 2 vCPU)
No API keys needed — model runs locally
"""
import os
import json
import uuid
import asyncio
import threading
from typing import AsyncGenerator, Dict, List
from contextlib import asynccontextmanager
from collections import defaultdict

import torch
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────
MODEL_NAME = "Qwen/Qwen3-1.7B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_NEW_TOKENS = 2048
MAX_CONVERSATION_HISTORY = 20  # Keep last 20 messages per session

SYSTEM_PROMPT = """أنت **CodeCraft** — وكيل برمجيات ذكي بالذكاء الاصطناعي.

هويتك:
- اسمك: CodeCraft
- وظيفتك: وكيل برمجيات ذكي متخصص في البرمجة والتطوير
- لا تقل أبداً أنك بوت محادثة أو مساعد عام
- أنت تتحدث كمهندس برمجيات حقيقي

قدراتك:
- كتابة كود بلغات متعددة (Python, JavaScript, TypeScript, Java, Go, Rust, C++)
- تحليل الأخطاء وإصلاحها
- فهم هيكل المشاريع
- تحسين أداء الكود

أسلوب عملك:
1. حلّل المطلوب أولاً
2. قدّم الكود في بلوكات واضحة
3. اكتب الكود الكامل
4. أجب باللغة التي يكتب بها المستخدم"""

# ── Conversation Memory ────────────────────────────────────────────────────
class ConversationMemory:
    """In-memory conversation storage per session."""

    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.lock = threading.Lock()

    def get_history(self, session_id: str) -> List[Dict]:
        with self.lock:
            return self.sessions.get(session_id, []).copy()

    def add_message(self, session_id: str, role: str, content: str):
        with self.lock:
            self.sessions[session_id].append({"role": role, "content": content})
            # Keep only last N messages to fit in context window
            if len(self.sessions[session_id]) > MAX_CONVERSATION_HISTORY:
                self.sessions[session_id] = self.sessions[session_id][-MAX_CONVERSATION_HISTORY:]

    def clear_session(self, session_id: str):
        with self.lock:
            self.sessions.pop(session_id, None)

memory = ConversationMemory()

# ── Pydantic Models ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    messages: list
    session_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048

class TerminalRequest(BaseModel):
    command: str

class GitCommitRequest(BaseModel):
    message: str

# ── Model Loading ──────────────────────────────────────────────────────────
class LocalModel:
    """Manages the local Qwen3 model."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.lock = threading.Lock()

    def load(self):
        if self.model is not None:
            return
        with self.lock:
            if self.model is not None:
                return
            print(f"[CodeCraft] Loading {MODEL_NAME} on {DEVICE}...")
            print(f"[CodeCraft] This may take 2-3 minutes on first load...")
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                trust_remote_code=True,
            )

            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                trust_remote_code=True,
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                device_map="auto" if DEVICE == "cuda" else None,
                low_cpu_mem_usage=True,
            )
            self.model.eval()
            print(f"[CodeCraft] Model loaded successfully!")

    def generate(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        self.load()

        # Build conversation for the model
        system_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        all_msgs = system_msgs + messages

        text = self.tokenizer.apply_chat_template(
            all_msgs,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,
                repetition_penalty=1.1,
                top_p=0.9 if temperature > 0 else None,
            )

        # Decode only the new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return response

    def generate_stream(self, messages: List[Dict], temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream tokens using a background thread."""
        self.load()
        import queue

        q = queue.Queue()

        def _generate():
            try:
                system_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
                all_msgs = system_msgs + messages

                text = self.tokenizer.apply_chat_template(
                    all_msgs,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

                # Use TextIteratorStreamer for streaming
                from transformers import TextIteratorStreamer

                streamer = TextIteratorStreamer(
                    self.tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )

                gen_kwargs = {
                    **inputs,
                    "max_new_tokens": max_tokens,
                    "temperature": temperature if temperature > 0 else None,
                    "do_sample": temperature > 0,
                    "repetition_penalty": 1.1,
                    "top_p": 0.9 if temperature > 0 else None,
                    "streamer": streamer,
                }

                thread = threading.Thread(
                    target=self.model.generate,
                    kwargs=gen_kwargs,
                    daemon=True,
                )
                thread.start()

                for chunk in streamer:
                    if chunk:
                        q.put(chunk)

                q.put(None)  # Signal completion
            except Exception as e:
                q.put(f"\n⚠️ Error: {str(e)}")
                q.put(None)

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

        while True:
            token = q.get()
            if token is None:
                break
            yield token


local_model = LocalModel()

# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🧠 CodeCraft — AI Coding Agent (100% Free)")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")
    print(f"RAM: ~4GB (Qwen3-1.7B)")
    print(f"Status: ✅ No API keys needed!")
    print("=" * 60)
    # Pre-load model in background
    threading.Thread(target=local_model.load, daemon=True).start()
    yield
    print("[CodeCraft] Shutting down...")

# ── FastAPI App ────────────────────────────────────────────────────────────
app = FastAPI(title="CodeCraft API", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Chat Endpoint ──────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Streaming chat endpoint with conversation memory."""

    session_id = request.session_id or str(uuid.uuid4())

    # Add user messages to memory
    for msg in request.messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                memory.add_message(session_id, "user", content)
            elif isinstance(content, list):
                # Extract text from content list
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        memory.add_message(session_id, "user", item.get("text", ""))

    # Get full conversation history from memory
    history = memory.get_history(session_id)

    async def generate():
        full_response = ""
        try:
            for token in local_model.generate_stream(
                history,
                request.temperature,
                request.max_tokens,
            ):
                full_response += token
                yield json.dumps({"token": token}) + "\n"

            # Save assistant response to memory
            memory.add_message(session_id, "assistant", full_response)

            # Send session_id for frontend to track
            yield json.dumps({"token": "", "session_id": session_id}) + "\n"

        except Exception as e:
            yield json.dumps({"token": f"\n⚠️ Error: {str(e)}\n"}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ── Memory Management ──────────────────────────────────────────────────────
@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str):
    """Clear conversation history for a session."""
    memory.clear_session(session_id)
    return {"message": "Memory cleared"}

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str):
    """Get conversation history for a session."""
    history = memory.get_history(session_id)
    return {"session_id": session_id, "messages": history}

# ── Terminal ───────────────────────────────────────────────────────────────
@app.post("/api/terminal")
async def terminal(request: TerminalRequest):
    """Execute a terminal command."""
    import subprocess
    try:
        result = subprocess.run(
            request.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout or result.stderr or "✅ Command executed (no output)"
        return {"output": output.strip()}
    except subprocess.TimeoutExpired:
        return {"output": "⏱️ Command timed out after 30s"}
    except Exception as e:
        return {"error": str(e)}

# ── Files ──────────────────────────────────────────────────────────────────
@app.get("/api/files")
async def list_files():
    """List project files."""
    import os
    files = []
    root = os.path.dirname(os.path.abspath(__file__))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != 'node_modules' and d != '__pycache__']
        rel_path = os.path.relpath(dirpath, root)
        for f in filenames:
            if f.startswith('.'):
                continue
            full = os.path.join(rel_path, f)
            try:
                size = os.path.getsize(os.path.join(dirpath, f))
                files.append({"path": full, "size": size})
            except:
                pass
    return {"files": sorted(files)}

# ── Git ────────────────────────────────────────────────────────────────────
@app.get("/api/git/status")
async def git_status():
    """Get git status."""
    import subprocess
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        return {"branch": branch, "staged": [], "unstaged": [], "ahead": 0, "behind": 0}
    except:
        return {"branch": "main", "staged": [], "unstaged": [], "ahead": 0, "behind": 0}

@app.post("/api/git/commit")
async def git_commit(request: GitCommitRequest):
    """Create a git commit."""
    import subprocess
    try:
        subprocess.run(["git", "add", "."], check=True, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", request.message],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return {"message": f"✅ Committed: {result.stdout.strip()}"}
        else:
            return {"message": f"ℹ️ {result.stdout.strip() or result.stderr.strip()}"}
    except Exception as e:
        return {"message": f"❌ Error: {str(e)}"}

# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "device": DEVICE,
        "api_keys_needed": False,
        "memory_enabled": True,
    }

# ── Serve Frontend ─────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

@app.get("/")
async def serve_index():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "message": "CodeCraft API — Frontend not built. Run: cd frontend && bun run build"
    })

@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    file_path = os.path.join(FRONTEND_DIST, "assets", path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ── Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    print(f"[CodeCraft] Starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
