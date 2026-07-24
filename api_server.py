"""
CodeCraft — AI Coding Agent v5.2
- Multi-key support: Groq, OpenAI, Gemini, HuggingFace
- Key rotation (auto-failover to next key on error)
- API endpoints for key management (add/list/delete/test)
- Keys stored in api_keys.json
"""
import os
import json
import uuid
import threading
import time
import queue as queue_module
import random
from typing import AsyncGenerator, List, Dict, Optional
from contextlib import asynccontextmanager
from collections import defaultdict
from pathlib import Path

# Load .env.local if it exists
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.local')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _val = _line.split('=', 1)
                _val = _val.strip('"\'')
                if _key not in os.environ:
                    os.environ[_key] = _val

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────
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

# ── API Key Store ──────────────────────────────────────────────────────────
KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_keys.json')

# Provider configs
PROVIDERS = {
    "groq": {
        "label": "Groq",
        "icon": "⚡",
        "base_url": "https://api.groq.com/openai/v1",
        "env_var": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    },
    "openai": {
        "label": "OpenAI",
        "icon": "🔵",
        "base_url": "https://api.openai.com/v1",
        "env_var": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    },
    "gemini": {
        "label": "Gemini",
        "icon": "🟢",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "env_var": "GEMINI_API_KEY",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
    },
    "hf": {
        "label": "HuggingFace",
        "icon": "🤗",
        "base_url": "https://api-inference.huggingface.co",
        "env_var": "HF_TOKEN",
        "models": ["Qwen/Qwen2.5-Coder-32B-Instruct"],
    },
}

class ApiKeyStore:
    def __init__(self):
        self._keys: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
        self._load_env_keys()
        self._load_file()

    def _load_env_keys(self):
        """Load keys from environment variables as default 'env' keys."""
        for provider, config in PROVIDERS.items():
            env_val = os.environ.get(config["env_var"], "")
            if env_val:
                self._keys[provider].append({
                    "id": "env",
                    "key": env_val,
                    "label": f"من البيئة (Environment)",
                    "active": True,
                })

    def _file_path(self) -> str:
        return KEYS_FILE

    def _load_file(self):
        """Load additional keys from JSON file."""
        try:
            if os.path.exists(self._file_path()):
                with open(self._file_path(), 'r') as f:
                    data = json.load(f)
                    for provider, keys in data.items():
                        if provider in PROVIDERS:
                            # Don't overwrite env key, add file keys
                            existing_ids = {k["id"] for k in self._keys[provider]}
                            for k in keys:
                                if k["id"] not in existing_ids:
                                    self._keys[provider].append(k)
        except Exception as e:
            print(f"[KeyStore] ⚠️ Could not load keys file: {e}")

    def _save_file(self):
        """Save non-env keys to JSON file."""
        try:
            data = {}
            for provider, keys in self._keys.items():
                file_keys = [k for k in keys if k["id"] != "env"]
                if file_keys:
                    data[provider] = file_keys
            with open(self._file_path(), 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[KeyStore] ⚠️ Could not save keys file: {e}")

    def get_keys(self, provider: str) -> List[Dict]:
        """Get all active keys for a provider."""
        with self._lock:
            return [k for k in self._keys.get(provider, []) if k.get("active", True)]

    def get_all(self) -> Dict[str, List[Dict]]:
        """Get all providers with their keys."""
        with self._lock:
            result = {}
            for provider in PROVIDERS:
                result[provider] = {
                    "config": PROVIDERS[provider],
                    "keys": self._keys.get(provider, []),
                }
            return result

    def add_key(self, provider: str, key: str, label: str = "") -> Dict:
        """Add a new API key for a provider. Returns the created key entry."""
        if provider not in PROVIDERS:
            raise ValueError(f"مزود غير مدعوم: {provider}")
        with self._lock:
            key_id = str(uuid.uuid4())[:8]
            entry = {
                "id": key_id,
                "key": key,
                "label": label or f"مفتاح {len(self._keys[provider]) + 1}",
                "active": True,
            }
            self._keys[provider].append(entry)
            self._save_file()
            return entry

    def delete_key(self, provider: str, key_id: str):
        """Delete a key by ID (cannot delete env key)."""
        if key_id == "env":
            raise ValueError("لا يمكن حذف مفتاح البيئة (Environment)")
        with self._lock:
            self._keys[provider] = [k for k in self._keys[provider] if k["id"] != key_id]
            self._save_file()

    def get_next_key(self, provider: str) -> Optional[str]:
        """Get the next active key for a provider (simple round-robin)."""
        keys = self.get_keys(provider)
        if not keys:
            return None
        # Simple rotation: pick a random key
        return random.choice(keys)["key"]

key_store = ApiKeyStore()

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

class AddKeyRequest(BaseModel):
    provider: str
    key: str
    label: str = ""

class TestKeyRequest(BaseModel):
    provider: str
    key: str

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
        Cascade with key rotation:
          Groq (key rotation) → OpenAI (key rotation) → Gemini (key rotation)
          → HF (key rotation) → Tiny Local
        """
        providers_to_try = ["groq", "openai", "gemini", "hf"]

        for provider in providers_to_try:
            keys = key_store.get_keys(provider)
            if not keys:
                continue

            # Try each key for this provider
            for key_entry in keys:
                try:
                    api_key = key_entry["key"]
                    if provider == "groq":
                        async for chunk in self._stream_openai_compat(api_key, PROVIDERS["groq"]["base_url"], "llama-3.3-70b-versatile", messages, max_tokens):
                            yield chunk
                        return
                    elif provider == "openai":
                        async for chunk in self._stream_openai_compat(api_key, PROVIDERS["openai"]["base_url"], "gpt-4o", messages, max_tokens):
                            yield chunk
                        return
                    elif provider == "gemini":
                        async for chunk in self._stream_gemini(api_key, messages, max_tokens):
                            yield chunk
                        return
                    elif provider == "hf":
                        async for chunk in self._stream_hf_api(api_key, messages, max_tokens):
                            yield chunk
                        return
                except Exception as e:
                    err_str = str(e)
                    print(f"[CodeCraft] ❌ {provider} key ({key_entry['id']}): {err_str}")
                    yield self._sse({"note": f"🔄 {PROVIDERS[provider]['icon']} {key_entry['label']} غير متاح، تجربة المفتاح التالي..."})

        # Check if local model is available as last resort
        if self._model_loaded:
            try:
                async for chunk in self._stream_local(messages, temperature, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"[CodeCraft] ❌ Local: {e}")

        # Check if any provider has keys at all
        total_keys = sum(len(key_store.get_keys(p)) for p in providers_to_try)
        if total_keys == 0:
            yield self._sse({"token": (
                "\n\n⚠️ **لم يتم تكوين أي مفتاح API بعد.**\n\n"
                "لتفعيل الذكاء:\n"
                "1. اذهب إلى **الإعدادات ← مفاتيح API**\n"
                "2. أضف مفتاحاً من أي مزود (Groq، OpenAI، Gemini، HuggingFace)\n"
                "3. Groq سريع ومجاني — اشترك في console.groq.com\n\n"
                "سيبدأ العمل فور إضافة المفتاح 🚀\n"
            )})
        else:
            yield self._sse({"token": "\n\n⚠️ جميع المفاتيح غير متاحة حالياً. حاول مرة أخرى أو أضف مفاتيح جديدة من الإعدادات.\n"})

    async def _stream_openai_compat(self, api_key: str, base_url: str, model: str, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from any OpenAI-compatible API."""
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        api_msgs = self.build_messages(messages)

        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                stream = client.chat.completions.create(
                    model=model,
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

    async def _stream_gemini(self, api_key: str, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from Gemini API."""
        import httpx
        api_msgs = self.build_messages(messages)

        # Build Gemini-format contents
        contents = []
        for msg in api_msgs[1:]:  # Skip system prompt
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        system_instruction = api_msgs[0]["content"] if api_msgs else ""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={api_key}&alt=sse"
        payload = {
            "contents": contents,
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            }
        }

        q: queue_module.Queue = queue_module.Queue()
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                with httpx.Client(timeout=120) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    for line in response.text.split("\n"):
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data == "[DONE]":
                                continue
                            try:
                                obj = json.loads(data)
                                candidates = obj.get("candidates", [])
                                if candidates:
                                    content = candidates[0].get("content", {})
                                    parts = content.get("parts", [])
                                    for part in parts:
                                        text = part.get("text", "")
                                        if text:
                                            q.put(text)
                            except json.JSONDecodeError:
                                pass
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

    async def _stream_hf_api(self, api_key: str, messages: list, max_tokens: int) -> AsyncGenerator[str, None]:
        """Stream from HuggingFace Inference API."""
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=api_key)
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
    print("🧠 CodeCraft — AI Coding Agent v5.2 (Multi-Key)")
    print("=" * 60)
    for p, cfg in PROVIDERS.items():
        k_count = len(key_store.get_keys(p))
        icon = cfg["icon"]
        print(f"  {icon} {cfg['label']}: {k_count} key(s)")
    print(f"🏠 Local: {LOCAL_MODEL}")
    print("=" * 60)
    threading.Thread(target=chat_handler.load_local, daemon=True).start()
    yield
    print("[CodeCraft] Shutting down...")

app = FastAPI(title="CodeCraft AI", version="5.2.0", lifespan=lifespan)
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

# ── API Key Management Endpoints ──────────────────────────────────────────
@app.get("/api/keys")
async def list_keys():
    """Get all providers with their configured keys (key values masked)."""
    data = key_store.get_all()
    # Mask key values for security
    for provider, info in data.items():
        for k in info["keys"]:
            key_val = k["key"]
            if len(key_val) > 8:
                k["key"] = key_val[:4] + "••••" + key_val[-4:]
            elif key_val:
                k["key"] = key_val[:4] + "••••"
    return data

@app.post("/api/keys")
async def add_key(request: AddKeyRequest):
    """Add a new API key for a provider."""
    try:
        entry = key_store.add_key(request.provider, request.key, request.label)
        # Rebuild the key store to include new keys in the chat handler
        return {"status": "ok", "key": {**entry, "key": entry["key"][:4] + "••••" + entry["key"][-4:]}}
    except ValueError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.delete("/api/keys/{provider}/{key_id}")
async def delete_key(provider: str, key_id: str):
    """Delete an API key."""
    try:
        key_store.delete_key(provider, key_id)
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/keys/test")
async def test_key(request: TestKeyRequest):
    """
    Test an API key and return detailed info:
    - status: ok/error
    - message: human-readable result
    - details: remaining credits, rate limits, plan info, usage
    """
    provider = request.provider
    api_key = request.key
    cfg = PROVIDERS.get(provider, {})

    def _build_result(ok: bool, msg: str, details: dict = None):
        return {
            "status": "ok" if ok else "error",
            "message": msg,
            "provider": provider,
            "details": details or {},
        }

    try:
        if provider == "groq":
            import httpx
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 5,
            }
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers, json=body,
                )
                if resp.status_code == 200:
                    # Extract rate limit info from headers
                    h = resp.headers
                    details = {
                        "plan": "Groq Free" if "groq" in str(h.get("x-groq", "")) else "Groq",
                        "remaining": {
                            "requests": h.get("x-ratelimit-remaining-requests", "غير معروف"),
                            "tokens": h.get("x-ratelimit-remaining-tokens", "غير معروف"),
                        },
                        "limit": {
                            "requests": h.get("x-ratelimit-limit-requests", "غير معروف"),
                            "tokens": h.get("x-ratelimit-limit-tokens", "غير معروف"),
                        },
                        "reset": h.get("x-ratelimit-reset-requests", ""),
                    }
                    # Try to parse as ints for display
                    try:
                        remaining_req = int(details["remaining"]["requests"])
                        remaining_tok = int(details["remaining"]["tokens"])
                        limit_req = int(details["limit"]["requests"])
                        limit_tok = int(details["limit"]["tokens"])
                        usage_pct_req = round((1 - remaining_req / limit_req) * 100) if limit_req else 0
                        usage_pct_tok = round((1 - remaining_tok / limit_tok) * 100) if limit_tok else 0
                        details["usage"] = {
                            "requests": f"{usage_pct_req}% من الحد مستخدم ({limit_req - remaining_req}/{limit_req})",
                            "tokens": f"{usage_pct_tok}% من الحد مستخدم ({limit_tok - remaining_tok}/{limit_tok})",
                        }
                        details["remaining"]["requests"] = f"{remaining_req:,}"
                        details["remaining"]["tokens"] = f"{remaining_tok:,}"
                        details["limit"]["requests"] = f"{limit_req:,}/ساعة"
                        details["limit"]["tokens"] = f"{limit_tok:,}/دقيقة"
                    except (ValueError, TypeError):
                        pass
                    return _build_result(True, f"✅ {cfg['label']} يعمل! الرصيد متاح", details)
                else:
                    err_body = resp.text[:200]
                    if resp.status_code == 401:
                        return _build_result(False, f"❌ مفتاح غير صالح — تحقق من المفتاح")
                    elif resp.status_code == 429:
                        return _build_result(False, f"❌ تم تجاوز حد الاستخدام (429) — انتظر ثم حاول مرة أخرى")
                    else:
                        return _build_result(False, f"❌ خطأ {resp.status_code}: {err_body[:100]}")

        elif provider == "openai":
            import httpx
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 5,
            }
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers, json=body,
                )
                if resp.status_code == 200:
                    h = resp.headers
                    details = {
                        "plan": "OpenAI API",
                        "remaining": {
                            "requests": h.get("x-ratelimit-remaining-requests", "غير معروف"),
                            "tokens": h.get("x-ratelimit-remaining-tokens", "غير معروف"),
                        },
                        "limit": {
                            "requests": h.get("x-ratelimit-limit-requests", "غير معروف"),
                            "tokens": h.get("x-ratelimit-limit-tokens", "غير معروف"),
                        },
                    }
                    # Try to get billing usage if possible
                    try:
                        # Check if key has billing data access
                        billing_resp = await client.get(
                            "https://api.openai.com/v1/dashboard/billing/credit_grants",
                            headers=headers,
                        )
                        if billing_resp.status_code == 200:
                            billing = billing_resp.json()
                            grants = billing.get("grants", [])
                            if grants:
                                details["balance"] = f"${grants[0].get('balance', 'N/A')}"
                    except Exception:
                        pass
                    return _build_result(True, f"✅ {cfg['label']} يعمل!", details)
                else:
                    err_body = resp.text[:200]
                    if resp.status_code == 401:
                        return _build_result(False, f"❌ مفتاح غير صالح — تحقق من المفتاح")
                    elif resp.status_code == 429:
                        return _build_result(False, f"❌ تم تجاوز حد الاستخدام (429)")
                    elif resp.status_code == 402:
                        return _build_result(False, f"❌ الرصيد منتهي (402) — تحتاج إلى إضافة رصيد")
                    else:
                        return _build_result(False, f"❌ خطأ {resp.status_code}: {err_body[:100]}")

        elif provider == "gemini":
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": "Say OK"}]}]}
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return _build_result(True, "✅ Gemini يعمل!", {
                        "plan": "Gemini Free (محدود)",
                        "remaining": {"requests": "60/دقيقة", "tokens": "غير معروف"},
                        "limit": {"requests": "60 طلب/دقيقة", "tokens": "1M/دقيقة"},
                    })
                elif resp.status_code == 403:
                    return _build_result(False, "❌ المفتاح ليس لديه صلاحية — قد يكون مقيداً")
                elif resp.status_code == 429:
                    return _build_result(False, "❌ تم تجاوز حد الاستخدام — انتظر ثم حاول مرة أخرى")
                else:
                    err = resp.text[:150]
                    return _build_result(False, f"❌ خطأ {resp.status_code}: {err[:100]}")

        elif provider == "hf":
            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}
            # First check: can we access the API?
            async with httpx.AsyncClient(timeout=20) as client:
                # Check token info
                whoami_resp = await client.get("https://huggingface.co/api/whoami-v2", headers=headers)
                if whoami_resp.status_code != 200:
                    return _build_result(False, "❌ مفتاح HuggingFace غير صالح")

                user_info = whoami_resp.json()
                user_name = user_info.get("name", "")
                can_use_inference = user_info.get("canPay", False) or user_info.get("isPro", False)

                # Try inference API call
                inf_payload = {
                    "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
                    "messages": [{"role": "user", "content": "Say OK"}],
                    "max_tokens": 5,
                }
                inf_resp = await client.post(
                    "https://api-inference.huggingface.co/v1/chat/completions",
                    headers=headers, json=inf_payload,
                )

                details = {
                    "plan": "HuggingFace Free" if not can_use_inference else "HuggingFace Pro/Paying",
                    "user": user_name,
                }

                if inf_resp.status_code == 200:
                    # Success - has inference access
                    details["remaining"] = {"requests": "رصيد متاح ✓"}
                    details["limit"] = {"requests": "حسب خطة HuggingFace", "tokens": "غير محدود (معتدل)"}
                    return _build_result(True, f"✅ HuggingFace يعمل! ({user_name})", details)
                elif inf_resp.status_code == 402:
                    details["remaining"] = {"requests": "⚠️ الرصيد منتهي"}
                    details["balance"] = "$0 — تحتاج إلى إضافة بطاقة دفع"
                    return _build_result(False, "❌ الرصيد الشهري منتهي — أضف بطاقة دفع", details)
                elif inf_resp.status_code == 429:
                    return _build_result(False, "❌ تم تجاوز حد الاستخدام — انتظر دقيقة", details)
                elif inf_resp.status_code == 503:
                    details["remaining"] = {"requests": "النموذج قيد التحميل"}
                    return _build_result(False, "⚠️ النموذج قيد التحميل على خوادم HF — حاول مرة أخرى", details)
                else:
                    err = inf_resp.text[:150]
                    return _build_result(False, f"❌ {err[:100]}", details)

    except Exception as e:
        return _build_result(False, f"❌ {str(e)[:120]}")

    return _build_result(False, "❌ لا يمكن التحقق من المفتاح")

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
        "version": "5.2.0",
        "groq": len(key_store.get_keys("groq")),
        "openai": len(key_store.get_keys("openai")),
        "gemini": len(key_store.get_keys("gemini")),
        "hf": len(key_store.get_keys("hf")),
        "local": chat_handler._model_loaded,
        "local_model": LOCAL_MODEL,
        "memory": True,
    }

# ── Frontend (SPA) ─────────────────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

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
