"""
CodeCraft — AI Coding Agent
Uses HuggingFace Inference API (fast, free) with local model fallback.
Fixed: async/sync blocking issues + proper SSE streaming.
"""
import os
import json
import uuid
import asyncio
import threading
import queue as queue_module
from typing import AsyncGenerator, Dict, List
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────
TEXT_MODEL  = os.environ.get('TEXT_MODEL',  'Qwen/Qwen2.5-Coder-32B-Instruct')
LOCAL_MODEL = os.environ.get('LOCAL_MODEL', 'Qwen/Qwen3-1.7B-Instruct')
HF_TOKEN    = os.environ.get('HF_TOKEN', '')
MAX_NEW_TOKENS = 2048
MAX_CONVERSATION_HISTORY = 20

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
- كتابة اختبارات وحدات

أسلوب عملك:
1. حلّل المطلوب أولاً
2. قدّم الكود في بلوكات واضحة
3. اكتب الكود الكامل لا أجزاء
4. أجب باللغة التي يكتب بها المستخدم"""

# ── Conversation Memory ────────────────────────────────────────────────────
class ConversationMemory:
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.lock = threading.Lock()

    def get_history(self, session_id: str) -> List[Dict]:
        with self.lock:
            return self.sessions.get(session_id, []).copy()

    def add_message(self, session_id: str, role: str, content: str):
        with self.lock:
            self.sessions[session_id].append({"role": role, "content": content})
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

# ── Chat Handler ───────────────────────────────────────────────────────────
class ChatHandler:
    def __init__(self):
        self.local_model = None
        self.local_tokenizer = None
        self.lock = threading.Lock()

    def load_local(self):
        if self.local_model is not None:
            return
        with self.lock:
            if self.local_model is not None:
                return
            print(f"[CodeCraft] Loading local model: {LOCAL_MODEL}...")
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.local_tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL, trust_remote_code=True)
            self.local_model = AutoModelForCausalLM.from_pretrained(
                LOCAL_MODEL,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            self.local_model.eval()
            print("[CodeCraft] Local model ready!")

    async def chat_stream(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Try HF API first, fallback to local model."""
        if HF_TOKEN:
            try:
                async for chunk in self._stream_hf_api(messages, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] HF API failed: {e}")
                yield self._sse({"token": f"\n⚠️ API unavailable, switching to local model...\n"})

        # Fallback to local model
        try:
            async for chunk in self._stream_local(messages, temperature, max_tokens):
                yield chunk
        except Exception as e:
            yield self._sse({"error": str(e)})

    async def _stream_hf_api(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from HuggingFace Inference API — runs sync client in thread pool."""
        from huggingface_hub import InferenceClient

        client = InferenceClient(model=TEXT_MODEL, token=HF_TOKEN)

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})
            elif isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            parts.append(item)
                if parts:
                    api_msgs.append({"role": role, "content": parts})

        # Use a thread-safe queue so the sync HF iterator runs in a thread
        # and does NOT block the asyncio event loop.
        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _fetch_sync():
            try:
                stream = client.chat_completion(
                    messages=api_msgs,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        q.put(delta)
            except Exception as e:
                q.put(e)
            finally:
                q.put(None)  # sentinel

        thread = threading.Thread(target=_fetch_sync, daemon=True)
        thread.start()

        while True:
            # run_in_executor lets us await a blocking q.get() without
            # stalling the event loop for other requests
            token = await loop.run_in_executor(None, q.get)
            if token is None:
                break
            if isinstance(token, Exception):
                raise token
            yield self._sse({"token": token})

    async def _stream_local(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from local model — runs generation in background thread."""
        import torch

        self.load_local()

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})

        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _generate():
            try:
                text = self.local_tokenizer.apply_chat_template(
                    api_msgs, tokenize=False, add_generation_prompt=True
                )
                inputs = self.local_tokenizer(text, return_tensors="pt").to(self.local_model.device)

                from transformers import TextIteratorStreamer
                streamer = TextIteratorStreamer(
                    self.local_tokenizer, skip_prompt=True, skip_special_tokens=True
                )

                gen_kwargs = {
                    **inputs,
                    "max_new_tokens": max_tokens,
                    "temperature": temperature if temperature > 0 else None,
                    "do_sample": temperature > 0,
                    "repetition_penalty": 1.1,
                    "streamer": streamer,
                }

                gen_thread = threading.Thread(
                    target=self.local_model.generate, kwargs=gen_kwargs, daemon=True
                )
                gen_thread.start()

                for chunk in streamer:
                    if chunk:
                        q.put(chunk)
                q.put(None)
            except Exception as e:
                q.put(e)
                q.put(None)

        threading.Thread(target=_generate, daemon=True).start()

        while True:
            # Non-blocking await — runs q.get() in executor thread
            token = await loop.run_in_executor(None, q.get)
            if token is None:
                break
            if isinstance(token, Exception):
                raise token
            yield self._sse({"token": token})

    @staticmethod
    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


chat_handler = ChatHandler()

# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🧠 CodeCraft — AI Coding Agent")
    print("=" * 60)
    print(f"API Model   : {TEXT_MODEL}")
    print(f"Local Model : {LOCAL_MODEL}")
    print(f"HF Token    : {'✅ Set' if HF_TOKEN else '❌ Not set (local only)'}")
    print("=" * 60)
    threading.Thread(target=chat_handler.load_local, daemon=True).start()
    yield
    print("[CodeCraft] Shutting down...")

# ── FastAPI App ────────────────────────────────────────────────────────────
app = FastAPI(title="CodeCraft API", version="5.0.0", lifespan=lifespan)

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

    for msg in request.messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                memory.add_message(session_id, "user", content)

    history = memory.get_history(session_id)

    async def generate():
        full_response = ""
        try:
            async for sse_chunk in chat_handler.chat_stream(history, request.temperature, request.max_tokens):
                yield sse_chunk
                try:
                    raw = sse_chunk.removeprefix("data: ").strip()
                    data = json.loads(raw)
                    if data.get("token"):
                        full_response += data["token"]
                except Exception:
                    pass

            if full_response:
                memory.add_message(session_id, "assistant", full_response)

            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ── Memory ─────────────────────────────────────────────────────────────────
@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str):
    memory.clear_session(session_id)
    return {"message": "Memory cleared"}

# ── Terminal ───────────────────────────────────────────────────────────────
@app.post("/api/terminal")
async def terminal(request: TerminalRequest):
    import subprocess
    try:
        result = subprocess.run(
            request.command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {"output": result.stdout + result.stderr}
    except subprocess.TimeoutExpired:
        return {"output": "Command timed out (30s limit)"}
    except Exception as e:
        return {"error": str(e)}

# ── Files ──────────────────────────────────────────────────────────────────
@app.get("/api/files")
async def list_files():
    import pathlib
    files = []
    try:
        for p in pathlib.Path(".").rglob("*"):
            if any(part.startswith(".") or part == "node_modules" or part == "__pycache__"
                   for part in p.parts):
                continue
            files.append({
                "name": p.name,
                "path": str(p),
                "type": "folder" if p.is_dir() else "file",
                "size": p.stat().st_size if p.is_file() else None,
            })
    except Exception:
        pass
    return {"files": files}

# ── Git ────────────────────────────────────────────────────────────────────
@app.get("/api/git/status")
async def git_status():
    import subprocess
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().splitlines()
        unstaged = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().splitlines()
        ahead_behind = subprocess.run(
            ["git", "rev-list", "--count", "--left-right", "@{upstream}...HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().split()
        behind = int(ahead_behind[0]) if len(ahead_behind) > 1 else 0
        ahead  = int(ahead_behind[1]) if len(ahead_behind) > 1 else 0
        return {"branch": branch, "staged": staged, "unstaged": unstaged, "ahead": ahead, "behind": behind}
    except Exception:
        return {"branch": "main", "staged": [], "unstaged": [], "ahead": 0, "behind": 0}

@app.post("/api/git/commit")
async def git_commit(request: GitCommitRequest):
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
    return {
        "status": "ok",
        "api_model": TEXT_MODEL,
        "local_model": LOCAL_MODEL,
        "hf_token": bool(HF_TOKEN),
        "memory_enabled": True,
        "version": "5.0.0",
    }

# ── Frontend (SPA) ─────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

# Serve built assets (JS/CSS chunks, images, etc.)
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    for name in ("favicon.svg", "favicon.ico"):
        p = os.path.join(FRONTEND_DIST, name)
        if os.path.exists(p):
            return FileResponse(p)
    return JSONResponse({}, status_code=404)

# SPA catch-all: every non-API route returns index.html so React Router works
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "CodeCraft API — Frontend not built yet"}, status_code=503)

# ── Entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    print(f"[CodeCraft] Starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
