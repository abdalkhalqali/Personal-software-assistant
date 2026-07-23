"""
CodeCraft — AI Coding Agent v5.1
Optimized cascade: Groq API → HF API → Tiny Local Model
Fixed: sync iterators no longer block the asyncio event loop;
       SSE static-file serving covers the full SPA.
"""
import os
import json
import uuid
import threading
import time
import queue as queue_module
from typing import AsyncGenerator, List, Dict, Optional
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
HF_TOKEN     = os.environ.get('HF_TOKEN', '')
LOCAL_MODEL  = os.environ.get('LOCAL_MODEL', 'Qwen/Qwen2.5-Coder-0.5B-Instruct')
MAX_NEW_TOKENS = 2048
MAX_CONVERSATION_HISTORY = 20

SYSTEM_PROMPT = """أنت **CodeCraft** — وكيل برمجيات ذكي بالذكاء الاصطناعي.

هويتك:
- اسمك: CodeCraft
- وظيفتك: وكيل برمجيات ذكي متخصص في البرمجة والتطوير
- لا تقل أبداً أنك بوت محادثة أو مساعد عام
- أنت تتحدث كمهندس برمجيات حقيقي خبير

قدراتك:
- كتابة كود بلغات متعددة (Python, JavaScript, TypeScript, Java, Go, Rust, C++)
- تحليل الأخطاء وإصلاحها
- فهم هيكل المشاريع وتطويرها
- تحسين أداء الكود
- كتابة اختبارات وحدات

أسلوب عملك:
1. حلّل المطلوب أولاً قبل الرد
2. قدّم الكود في بلوكات واضحة مع الشرح
3. اكتب الكود الكامل لا أجزاء
4. أجب باللغة التي يكتب بها المستخدم (عربي أو إنجليزي)"""

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
        self.model_lock = threading.Lock()
        self._model_loaded = False
        self._model_attempted = False

    def load_local(self):
        """Try to load a tiny local model if disk space allows."""
        if self._model_attempted:
            return
        with self.model_lock:
            if self._model_attempted:
                return
            self._model_attempted = True
            print(f"[CodeCraft] 🔄 Checking local model: {LOCAL_MODEL}")
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024 ** 3)
            if free_gb < 1.0:
                print(f"[CodeCraft] ⏭️ Skipping local model (only {free_gb:.1f}GB free)")
                return
            t0 = time.time()
            try:
                import torch
                cpu_count = os.cpu_count() or 2
                torch.set_num_threads(max(1, cpu_count - 1))
                from transformers import AutoModelForCausalLM, AutoTokenizer
                self.local_tokenizer = AutoTokenizer.from_pretrained(
                    LOCAL_MODEL, trust_remote_code=True
                )
                self.local_model = AutoModelForCausalLM.from_pretrained(
                    LOCAL_MODEL,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )
                self.local_model.eval()
                self._model_loaded = True
                print(f"[CodeCraft] ✅ Local model ready in {time.time()-t0:.1f}s")
            except Exception as e:
                print(f"[CodeCraft] ⚠️ Local model load failed: {e}")

    def build_messages(self, messages: list) -> list:
        """Build messages array with system prompt."""
        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})
        return api_msgs

    async def chat_stream(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """
        Cascade: Groq (fastest) → HF API → Tiny Local (last resort).
        If all fail, returns a friendly Arabic error.
        """
        providers_available = 0

        if GROQ_API_KEY:
            providers_available += 1
            try:
                async for chunk in self._stream_groq(messages, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] ❌ Groq: {e}")
                yield self._sse({"note": "🔄 Switching provider..."})

        if HF_TOKEN:
            providers_available += 1
            try:
                import torch
                cpu_count = os.cpu_count() or 2
                torch.set_num_threads(max(1, cpu_count - 1))
                from transformers import AutoModelForCausalLM, AutoTokenizer
                self.local_tokenizer = AutoTokenizer.from_pretrained(
                    LOCAL_MODEL, trust_remote_code=True
                )
                self.local_model = AutoModelForCausalLM.from_pretrained(
                    LOCAL_MODEL,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )
                self.local_model.eval()
                self._model_loaded = True
                print(f"[CodeCraft] ✅ Local model ready in {time.time()-t0:.1f}s")
            except Exception as e:
                print(f"[CodeCraft] ❌ HF API: {e}")
                yield self._sse({"note": "🔄 Trying backup..."})

        if self._model_loaded:
            providers_available += 1
            try:
                async for chunk in self._stream_local(messages, temperature, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] ❌ Local: {e}")

        if providers_available == 0:
            yield self._sse({"token": (
                "\n\n⚠️ **لم يتم تكوين أي مزود ذكاء اصطناعي بعد.**\n\n"
                "لتفعيل الذكاء:\n"
                "1. أضف `GROQ_API_KEY` في الأسرار (مفاتيح API) — سريع ومجاني\n"
                "2. أو أضف `HF_TOKEN` — Hugging Face API\n\n"
                "سيبدأ العمل فور إضافة أي منهما 🚀\n"
            )})
        else:
            yield self._sse({"token": "\n\n⚠️ عذراً، جميع مزودي الذكاء غير متاحين حالياً. حاول مرة أخرى.\n"})

    # ── FIX: sync Groq iterator runs in thread pool, not blocking event loop ──
    async def _stream_groq(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from Groq Cloud (Llama 70B via OpenAI compat API)."""
        from openai import OpenAI
        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        api_msgs = self.build_messages(messages)

        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
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
                q.put(None)

        threading.Thread(target=_fetch, daemon=True).start()

        while True:
            token = await loop.run_in_executor(None, q.get)
            if token is None:
                break
            if isinstance(token, Exception):
                raise token
            yield self._sse({"token": token})

    # ── FIX: sync HF iterator runs in thread pool, not blocking event loop ──
    async def _stream_hf_api(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from HuggingFace Inference API (Qwen2.5-Coder-32B)."""
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=HF_TOKEN)
        api_msgs = self.build_messages(messages)

        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                stream = client.chat_completion(
                    messages=api_msgs,
                    model="Qwen/Qwen2.5-Coder-32B-Instruct",
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
                q.put(None)

        threading.Thread(target=_fetch, daemon=True).start()

        while True:
            token = await loop.run_in_executor(None, q.get)
            if token is None:
                break
            if isinstance(token, Exception):
                raise token
            yield self._sse({"token": token})

    # ── FIX: q.get() runs in executor instead of blocking event loop ──
    async def _stream_local(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from local CPU model (tiny fallback)."""
        import torch
        api_msgs = self.build_messages(messages)
        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _generate():
            try:
                text = self.local_tokenizer.apply_chat_template(
                    api_msgs, tokenize=False, add_generation_prompt=True
                )
                inputs = self.local_tokenizer(text, return_tensors="pt")
                inputs = {k: v.to(self.local_model.device) for k, v in inputs.items()}
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
                print(f"[CodeCraft] Local error: {e}")
                q.put(e)
                q.put(None)

        threading.Thread(target=_generate, daemon=True).start()

        while True:
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
    print("🧠 CodeCraft — AI Coding Agent v5.1")
    print("=" * 60)
    print(f"⚡ Groq:  {'✅ ' + GROQ_API_KEY[:8] + '...' if GROQ_API_KEY else '⏸️  Not set'}")
    print(f"🌐 HF:    {'✅ ' + HF_TOKEN[:8] + '...' if HF_TOKEN else '⏸️  Not set'}")
    print(f"🏠 Local: {LOCAL_MODEL} (will check disk space)")
    print("=" * 60)
    threading.Thread(target=chat_handler.load_local, daemon=True).start()
    yield
    print("[CodeCraft] Shutting down...")

app = FastAPI(title="CodeCraft AI", version="5.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Chat ───────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(request: ChatRequest):
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
    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

# ── Other Endpoints ────────────────────────────────────────────────────────
@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str):
    memory.clear_session(session_id)
    return {"message": "Memory cleared"}

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str):
    return {"history": memory.get_history(session_id)}

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

@app.get("/api/files")
async def list_files():
    import pathlib
    files = []
    try:
        for p in pathlib.Path(".").rglob("*"):
            if any(part.startswith(".") or part in ("node_modules", "__pycache__")
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
    return {"files": sorted(files, key=lambda f: f["path"])}

@app.get("/api/git/status")
async def git_status():
    import subprocess
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return {"branch": branch, "staged": [], "unstaged": [], "ahead": 0, "behind": 0}
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
        return {"message": f"ℹ️ {result.stdout.strip() or result.stderr.strip()}"}
    except Exception as e:
        return {"message": f"❌ Error: {str(e)}"}

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "5.1.0",
        "groq": bool(GROQ_API_KEY),
        "hf": bool(HF_TOKEN),
        "local": chat_handler._model_loaded,
        "local_model": LOCAL_MODEL,
        "memory": True,
    }

# ── Frontend (SPA) ─────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

# Serve /assets/* statically (JS/CSS bundles, images, fonts)
_assets_dir = os.path.join(FRONTEND_DIST, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    for name in ("favicon.svg", "favicon.ico"):
        p = os.path.join(FRONTEND_DIST, name)
        if os.path.exists(p):
            return FileResponse(p)
    return JSONResponse({}, status_code=404)

# SPA catch-all: all non-API routes return index.html (supports React Router)
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "CodeCraft API — frontend not built yet"},
        status_code=503,
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
