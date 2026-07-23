"""
CodeCraft — AI Coding Agent
Local-first architecture: optimized CPU model → Groq API → HuggingFace API
Authoritative Coding Agent with Arabic support.
"""
import os
import json
import uuid
import asyncio
import threading
import time
from typing import AsyncGenerator, Dict, List, Optional
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────
LOCAL_MODEL = os.environ.get('LOCAL_MODEL', 'Qwen/Qwen3-1.7B-Instruct')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
HF_TOKEN = os.environ.get('HF_TOKEN', '')
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

    def load_local(self):
        """Load the local CPU model with optimizations."""
        if self._model_loaded:
            return
        with self.model_lock:
            if self._model_loaded:
                return
            print(f"[CodeCraft] 🔄 Loading local model: {LOCAL_MODEL}...")
            t0 = time.time()
            import torch
            # Optimize CPU threads
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
            elapsed = time.time() - t0
            print(f"[CodeCraft] ✅ Local model ready in {elapsed:.1f}s")

    async def chat_stream(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Cascade: Local (primary) → Groq → HF API (fallbacks)."""
        # 1️⃣ Local model (always available, free forever)
        try:
            async for chunk in self._stream_local(messages, temperature, max_tokens):
                yield chunk
            return
        except Exception as e:
            err_msg = str(e)
            print(f"[CodeCraft] ❌ Local model failed: {err_msg[:100]}")
            yield self._sse({"warning": True, "token": ""})

        # 2️⃣ Groq API (fast fallback, if key available)
        if GROQ_API_KEY:
            try:
                async for chunk in self._stream_groq(messages, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] ❌ Groq failed: {e}")
                yield self._sse({"warning": True, "token": ""})

        # 3️⃣ HF Inference API (last resort, if token available)
        if HF_TOKEN:
            try:
                async for chunk in self._stream_hf_api(messages, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] ❌ HF API failed: {e}")
                yield self._sse({"warning": True, "token": ""})

        # 😢 All failed
        yield self._sse({"token": "\n\n⚠️ عذراً، جميع مزودي الذكاء غير متاحين حالياً. حاول مرة أخرى لاحقاً.\n"})

    async def _stream_local(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from local CPU model (primary)."""
        import torch
        import queue

        self.load_local()
        if not self._model_loaded:
            raise RuntimeError("Local model failed to load")

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})

        q = queue.Queue()

        def _generate():
            try:
                text = self.local_tokenizer.apply_chat_template(
                    api_msgs, tokenize=False, add_generation_prompt=True
                )
                inputs = self.local_tokenizer(text, return_tensors="pt")
                # Ensure inputs are on the right device
                inputs = {k: v.to(self.local_model.device) for k, v in inputs.items()}

                from transformers import TextIteratorStreamer
                streamer = TextIteratorStreamer(
                    self.local_tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )

                gen_kwargs = {
                    **inputs,
                    "max_new_tokens": max_tokens,
                    "temperature": temperature if temperature > 0 else None,
                    "do_sample": temperature > 0,
                    "repetition_penalty": 1.1,
                    "streamer": streamer,
                }

                thread = threading.Thread(target=self.local_model.generate, kwargs=gen_kwargs, daemon=True)
                thread.start()

                for chunk in streamer:
                    if chunk:
                        q.put(chunk)
                q.put(None)
            except Exception as e:
                print(f"[CodeCraft] Local gen error: {e}")
                q.put(f"\n\n⚠️ خطأ في التوليد المحلي: {e}\n")
                q.put(None)

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

        while True:
            token = q.get()
            if token is None:
                break
            yield self._sse({"token": token})

    async def _stream_groq(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from Groq Cloud API (fast fallback)."""
        from openai import OpenAI

        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})

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
                yield self._sse({"token": delta})

    async def _stream_hf_api(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from HuggingFace Inference API (last resort)."""
        from huggingface_hub import InferenceClient

        client = InferenceClient(token=HF_TOKEN)

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                api_msgs.append({"role": role, "content": content})

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
                yield self._sse({"token": delta})

    @staticmethod
    def _sse(data: dict) -> str:
        """Format as Server-Sent Event."""
        return f"data: {json.dumps(data)}\n\n"


chat_handler = ChatHandler()

# ── Providers info ─────────────────────────────────────────────────────────
def get_provider_status() -> dict:
    return {
        "local": LOCAL_MODEL,
        "local_loaded": chat_handler._model_loaded,
        "groq": bool(GROQ_API_KEY),
        "hf_api": bool(HF_TOKEN),
    }

# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🧠 CodeCraft — AI Coding Agent v5.0")
    print("=" * 60)
    print(f"🏠 Local model: {LOCAL_MODEL}")
    print(f"⚡ Groq API:    {'✅ Ready' if GROQ_API_KEY else '⏸️  Not configured'}")
    print(f"🌐 HF API:      {'✅ Ready' if HF_TOKEN else '⏸️  Not configured'}")
    print("=" * 60)
    print("🔄 Loading local model in background...")
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

    # Add user messages to memory
    for msg in request.messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                memory.add_message(session_id, "user", content)

    # Get full conversation history
    history = memory.get_history(session_id)

    async def generate():
        full_response = ""
        try:
            async for sse_chunk in chat_handler.chat_stream(history, request.temperature, request.max_tokens):
                yield sse_chunk
                # Extract token for memory
                if "data: " in sse_chunk:
                    try:
                        data = json.loads(sse_chunk.replace("data: ", "").strip())
                        if data.get("token"):
                            full_response += data["token"]
                    except:
                        pass

            # Save assistant response to memory
            if full_response:
                memory.add_message(session_id, "assistant", full_response)

            # Send done signal with session_id
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

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str):
    history = memory.get_history(session_id)
    return {"session_id": session_id, "messages": history}

# ── Terminal ───────────────────────────────────────────────────────────────
@app.post("/api/terminal")
async def terminal(request: TerminalRequest):
    import subprocess
    try:
        result = subprocess.run(request.command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr or "✅ Command executed (no output)"
        return {"output": output.strip()}
    except subprocess.TimeoutExpired:
        return {"output": "⏱️ Command timed out after 30s"}
    except Exception as e:
        return {"error": str(e)}

# ── Files ──────────────────────────────────────────────────────────────────
@app.get("/api/files")
async def list_files():
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
    import subprocess
    try:
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        return {"branch": branch, "staged": [], "unstaged": [], "ahead": 0, "behind": 0}
    except:
        return {"branch": "main", "staged": [], "unstaged": [], "ahead": 0, "behind": 0}

@app.post("/api/git/commit")
async def git_commit(request: GitCommitRequest):
    import subprocess
    try:
        subprocess.run(["git", "add", "."], check=True, timeout=10)
        result = subprocess.run(["git", "commit", "-m", request.message], capture_output=True, text=True, timeout=10)
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
        "providers": get_provider_status(),
        "memory_enabled": True,
    }

# ── Frontend ───────────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

@app.get("/")
async def serve_index():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "CodeCraft API — Frontend not built"})

@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    file_path = os.path.join(FRONTEND_DIST, "assets", path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ── Entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    print(f"[CodeCraft] Starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
