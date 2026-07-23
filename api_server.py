"""
Personal AI Coding Agent — API Server
Serves the React frontend and provides AI inference + GitHub integration endpoints.
"""
import os
import re
import json
import base64
import asyncio
import traceback
import urllib.request
import urllib.error
import urllib.parse
from typing import AsyncGenerator
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import gradio as gr

# ── Config ─────────────────────────────────────────────────────────────────
CHECKPOINT     = os.environ.get('MODEL_CHECKPOINT', 'Qwen/Qwen3-VL-2B-Instruct')
TEXT_MODEL     = os.environ.get('TEXT_MODEL', 'Qwen/Qwen2.5-Coder-32B-Instruct')
DEVICE         = 'cuda' if torch.cuda.is_available() else 'cpu'
MAX_NEW_TOKENS = int(os.environ.get('MAX_NEW_TOKENS', '3072'))
HF_TOKEN       = os.environ.get('HF_TOKEN', '')

SYSTEM_PROMPT = """أنت **CodeCraft** — وكيل برمجيات ذكي بالذكاء الاصطناعي. أنت لست بوت محادثة عادياً، أنت مهندس برمجيات محترف يعمل في بيئة تطوير متكاملة.

**هويتك:**
- اسمك: CodeCraft
- وظيفتك: وكيل برمجيات ذكي متخصص في البرمجة والتطوير
- لا تقل أبداً أنك بوت محادثة أو مساعد عام
- أنت تتحدث كمهندس برمجيات حقيقي لديه خبرة في جميع لغات البرمجة

**قدراتك البرمجية:**
- كتابة كود بلغات متعددة (Python, JavaScript, TypeScript, Java, Go, Rust, C++, PHP, Ruby)
- تحليل الأخطاء وإصلاحها بدقة
- كتابة اختبارات وحدات وتكامل
- فهم هيكل المشاريع الكبيرة
- تحسين أداء الكود
- تطبيق أفضل الممارسات

**أسلوب عملك:**
1. حلّل المطلوب أولاً
2. اشرح خطتك بوضوح
3. قدّم الكود في بلوكات واضحة
4. اكتب الكود الكامل لا أجزاء
5. اقترح تحسينات إضافية

أجب باللغة التي يكتب بها المستخدم. لا تستخدم أي صيغة تبدأ بـ 'أنا بوت' أو 'أنا مساعد' — أنت **CodeCraft وكيل البرمجة**."""

# ── Pydantic Models ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    messages: list
    mode: str = "developer"
    temperature: float = 0.7
    max_tokens: int = 3072

class TerminalRequest(BaseModel):
    command: str

class GitCommitRequest(BaseModel):
    message: str

# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[API] Starting AI Coding Agent API Server")
    print(f"[API] Model: {CHECKPOINT}")
    print(f"[API] Device: {DEVICE}")
    print(f"[API] HF Inference API: {'✅ Enabled' if HF_TOKEN else '❌ Disabled (set HF_TOKEN)'}")
    yield
    print("[API] Shutting down...")

# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(title="AI Coding Agent API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ──────────────────────────────────────────────────────────────

class ChatHandler:
    """Handles AI inference - tries HF Inference API first, falls back to local CPU."""

    def __init__(self):
        self.model = None
        self.processor = None

    def load_local(self):
        if self.model is not None:
            return
        print("[Agent] Loading local model...")
        from transformers import AutoProcessor, AutoModelForImageTextToText
        self.processor = AutoProcessor.from_pretrained(CHECKPOINT, trust_remote_code=True)
        dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
        self.model = AutoModelForImageTextToText.from_pretrained(
            CHECKPOINT,
            trust_remote_code=True,
            torch_dtype=dtype,
            device_map="auto" if DEVICE == "cuda" else "cpu",
        )
        self.model.eval()
        print("[Agent] Local model ready")

    async def chat_stream(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream chat response from HF Inference API or local model."""
        if HF_TOKEN:
            try:
                async for token in self._stream_api(messages, max_tokens):
                    yield token
                return
            except Exception as e:
                yield json.dumps({"token": f"\n⚠️ API unavailable, switching to local CPU...\n"})
                print(f"[Agent] API failed: {e}")

        async for token in self._stream_local(messages, temperature, max_tokens):
            yield token

    async def _stream_api(self, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        from huggingface_hub import InferenceClient
        client = InferenceClient(model=TEXT_MODEL, token=HF_TOKEN)

        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            if isinstance(msg.get("content"), str):
                api_msgs.append({"role": msg["role"], "content": msg["content"]})
            elif isinstance(msg.get("content"), list):
                parts = []
                has_image = False
                for item in msg["content"]:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image":
                            has_image = True
                            parts.append({"type": "image_url", "image_url": {"url": item.get("image", "")}})
                if has_image:
                    client = InferenceClient(model=CHECKPOINT, token=HF_TOKEN)
                if parts:
                    api_msgs.append({"role": msg["role"], "content": parts})

        stream = client.chat_completion(
            messages=api_msgs,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield json.dumps({"token": delta})

        yield json.dumps({"token": "\n\n✅ تم إكمال الرد."})

    async def _stream_local(self, messages: list, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
        import threading
        self.load_local()
        from qwen_vl_utils import process_vision_info
        from transformers import TextIteratorStreamer

        history = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        text = self.processor.apply_chat_template(history, tokenize=False, add_generation_prompt=True)

        image_inputs, video_inputs = process_vision_info(history)
        inputs = self.processor(
            text=[text],
            images=image_inputs or None,
            videos=video_inputs or None,
            padding=True,
            return_tensors="pt",
        ).to(self.model.device if hasattr(self.model, "device") else DEVICE)

        streamer = TextIteratorStreamer(self.processor, skip_prompt=True, skip_special_tokens=True)
        gen_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            repetition_penalty=1.05,
        )

        thread = threading.Thread(target=self.model.generate, kwargs=gen_kwargs, daemon=True)
        thread.start()

        for chunk in streamer:
            yield json.dumps({"token": chunk})


chat_handler = ChatHandler()


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Streaming chat endpoint."""
    return StreamingResponse(
        chat_handler.chat_stream(request.messages, request.temperature, request.max_tokens),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@app.get("/api/files")
async def list_files():
    """List project files."""
    import os
    files = []
    root = os.path.dirname(os.path.abspath(__file__))
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden dirs and node_modules
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


@app.get("/api/git/status")
async def git_status():
    """Get git status."""
    import subprocess
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().split('\n') if subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip() else []

        staged = [s[3:] for s in status if s.startswith('M ')]
        unstaged = [s[3:] for s in status if s.startswith(' M') or s.startswith('??')]

        return {"branch": branch, "staged": staged, "unstaged": unstaged, "ahead": 0, "behind": 0}
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


# ── Serve React Frontend ───────────────────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")


@app.get("/")
async def serve_index():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "AI Coding Agent API Server — Frontend not built yet. Run 'cd frontend && bun run build'"},
        status_code=200,
    )


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
    print(f"[API] Starting server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
