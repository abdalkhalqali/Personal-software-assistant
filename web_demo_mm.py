"""
Personal AI Coding Agent — Qwen3-VL
مساعد البرمجة الشخصي الذكي

وضع التشغيل (محدد تلقائياً):
  1. HF Inference API  → يستخدم HF_TOKEN، بدون ZeroGPU، مجاني بلا حدود يومية
  2. GPU محلي          → إن توفّر (ZeroGPU أو GPU حقيقي)
  3. CPU محلي          → الاحتياط الأخير، بطيء لكن مجاني دائماً
"""
import os
import re
import base64
import json
import traceback
import urllib.request
import urllib.error
import urllib.parse
import torch
import gradio as gr
from threading import Thread
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

# ── ZeroGPU (مطلوب على هاردوير zero-gpu وإلا يتوقف التطبيق) ───────────────
try:
    import spaces
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False

# ── Config ─────────────────────────────────────────────────────────────────
CHECKPOINT     = os.environ.get('MODEL_CHECKPOINT', 'Qwen/Qwen3-VL-2B-Instruct')
DEVICE         = 'cuda' if torch.cuda.is_available() else 'cpu'
MAX_NEW_TOKENS = int(os.environ.get('MAX_NEW_TOKENS', '3072'))
HF_TOKEN       = os.environ.get('HF_TOKEN', '')

# HF Inference API أولاً — يعمل على سيرفرات HF البعيدة (لا يستهلك GPU الـ Space)
# GPU الـ Space يُستخدم فقط كـ fallback إذا فشل الـ API
USE_API = os.environ.get('USE_API', '1') == '1' and bool(HF_TOKEN)
IMAGE_EXTS     = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.avif')
VIDEO_EXTS     = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v')

SYSTEM_PROMPT = """أنت مساعد برمجة شخصي ذكي ومتقدم. لديك قدرات متعددة:

**قدراتك البرمجية:**
- قراءة وفهم الكود بجميع لغات البرمجة
- تحليل الأخطاء واقتراح الإصلاحات بدقة
- كتابة وتعديل الكود بجودة عالية
- فهم هيكل المشاريع والعلاقات بين الملفات
- اقتراح أفضل الممارسات والهندسة المعمارية
- مراجعة الكود وتحسين الأداء والأمان

**قدراتك البصرية:**
- تحليل لقطات الشاشة وصور الأخطاء
- قراءة مخططات قواعد البيانات والمعمارية
- فهم واجهات المستخدم واقتراح التحسينات
- قراءة رموز QR واستخراج النصوص من الصور

**أسلوب عملك:**
1. افهم المطلوب أولاً قبل أي تعديل
2. اشرح خطتك بوضوح قبل التنفيذ
3. قدّم الكود في بلوكات واضحة مع اسم الملف
4. نبّه دائماً إذا كان التعديل قد يسبب مشاكل
5. اعمل بشكل منهجي خطوة بخطوة
6. اكتب الكود الكامل وليس مجرد أجزاء

**تنسيق ردودك:**
- عند كتابة كود لملف معين استخدم: ```python:اسم_الملف.py
- عند كتابة أوامر terminal استخدم: ```bash
- اشرح دائماً ماذا فعلت ولماذا
- أجب باللغة التي يكتب بها المستخدم (عربي أو إنجليزي)"""

# ── GitHub API Client ───────────────────────────────────────────────────────

class GitHubClient:
    """Minimal GitHub REST API client using only stdlib."""

    BASE = "https://api.github.com"

    def __init__(self, token: str = ""):
        self.token = token.strip()

    def _headers(self):
        h = {"Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(self, method: str, path: str, body=None) -> dict | list:
        url = self.BASE + path
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            msg = json.loads(e.read().decode()).get("message", str(e))
            raise RuntimeError(f"GitHub API {e.code}: {msg}")

    def get_repo(self, owner: str, repo: str) -> dict:
        return self._request("GET", f"/repos/{owner}/{repo}")

    def get_tree(self, owner: str, repo: str, sha: str = "HEAD") -> list:
        data = self._request("GET", f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
        return data.get("tree", [])

    def get_branches(self, owner: str, repo: str) -> list[str]:
        data = self._request("GET", f"/repos/{owner}/{repo}/branches")
        return [b["name"] for b in data]

    def get_file(self, owner: str, repo: str, path: str, branch: str = "main") -> tuple[str, str]:
        """Returns (content_str, sha)."""
        data = self._request("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content, data["sha"]

    def update_file(self, owner: str, repo: str, path: str, branch: str,
                    message: str, content: str, sha: str | None = None) -> dict:
        """Create or update a file. sha is required for updates."""
        body = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        return self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", body)

    def create_file(self, owner: str, repo: str, path: str, branch: str,
                    message: str, content: str) -> dict:
        return self.update_file(owner, repo, path, branch, message, content, sha=None)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or 'owner/repo' string."""
    url = url.strip().rstrip("/")
    # Handle owner/repo format
    if "/" in url and "github.com" not in url:
        parts = url.split("/")
        return parts[0], parts[1]
    # Handle full URLs
    m = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(f"تعذّر استخراج معلومات المستودع من: {url}")


# ── Model (local — CPU/GPU fallback) ───────────────────────────────────────
model = None
processor = None


def load_model_once():
    """تحميل النموذج محلياً (CPU أو GPU). يُستدعى فقط إن فشل الـ API."""
    global model, processor
    if model is not None:
        return
    print(f"[Agent] تحميل النموذج محلياً على {DEVICE}…")
    processor = AutoProcessor.from_pretrained(CHECKPOINT, trust_remote_code=True)

    dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
    load_kwargs = dict(trust_remote_code=True, torch_dtype=dtype)

    if DEVICE == "cuda":
        load_kwargs["device_map"] = "auto"
        try:
            import flash_attn  # noqa: F401
            load_kwargs["attn_implementation"] = "flash_attention_2"
            print("[Agent] ✅ FlashAttention2 مُفعَّلة")
        except ImportError:
            load_kwargs["attn_implementation"] = "sdpa"
            print("[Agent] ℹ️ SDPA مُفعَّل")
    else:
        load_kwargs["device_map"] = "cpu"

    model = AutoModelForImageTextToText.from_pretrained(CHECKPOINT, **load_kwargs)
    model.eval()
    print("[Agent] ✅ النموذج المحلي جاهز")


# ── HF Inference API helpers ────────────────────────────────────────────────

MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif",  "webp": "image/webp", "bmp": "image/bmp",
    "tiff": "image/tiff","tif": "image/tiff",  "avif": "image/avif",
}


def _img_to_data_url(path: str) -> str | None:
    """اقرأ صورة من المسار وحوّلها إلى data-URL لإرسالها عبر API."""
    try:
        ext = path.rsplit(".", 1)[-1].lower()
        mime = MIME.get(ext, "image/jpeg")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _history_to_api(history: list) -> list:
    """
    حوّل تاريخ المحادثة من صيغة Qwen المحلية إلى صيغة OpenAI-chat المتوافقة مع HF API.
    الصور المحلية تُحوَّل إلى data-URL (base64).
    """
    api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in (history or []):
        role    = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            api_msgs.append({"role": role, "content": content})
            continue

        # محتوى متعدد الوسائط (قائمة)
        parts = []
        for item in content:
            t = item.get("type", "")
            if t == "text":
                parts.append({"type": "text", "text": item.get("text", "")})
            elif t == "image":
                path = item.get("image", "")
                url  = _img_to_data_url(path) if path else None
                if url:
                    parts.append({"type": "image_url", "image_url": {"url": url}})
                else:
                    parts.append({"type": "text", "text": f"[صورة: {path}]"})
            elif t == "video":
                parts.append({"type": "text",
                               "text": "[فيديو مرفق — التحليل البصري للفيديو غير مدعوم عبر API]"})
        if parts:
            api_msgs.append({"role": role, "content": parts})

    return api_msgs


def _predict_api(chatbot, history):
    """استدلال عبر HF Inference API — لا يستهلك ZeroGPU."""
    from huggingface_hub import InferenceClient

    client   = InferenceClient(model=CHECKPOINT, token=HF_TOKEN)
    api_msgs = _history_to_api(history)

    reply   = ""
    chatbot = list(chatbot or []) + [{"role": "assistant", "content": "⏳ جاري التفكير…"}]
    history = list(history or []) + [{"role": "assistant", "content": ""}]

    try:
        stream = client.chat_completion(
            messages=api_msgs,
            max_tokens=MAX_NEW_TOKENS,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            reply += delta
            chatbot[-1] = {"role": "assistant", "content": reply}
            history[-1] = {"role": "assistant", "content": reply}
            yield chatbot, history
    except Exception as e:
        raise RuntimeError(str(e))


def _predict_local(chatbot, history):
    """استدلال محلي (CPU/GPU) — احتياطي إذا فشل API."""
    load_model_once()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history or [])
    try:
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs or None,
            videos=video_inputs or None,
            padding=True,
            return_tensors="pt",
        ).to(model.device if hasattr(model, "device") else DEVICE)
    except Exception:
        err = f"⚠️ خطأ في المعالجة:\n```\n{traceback.format_exc()}\n```"
        yield list(chatbot or []) + [{"role": "assistant", "content": err}], history
        return

    streamer = TextIteratorStreamer(processor, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(
        **inputs, streamer=streamer,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False, temperature=None, top_p=None,
        repetition_penalty=1.05,
    )
    Thread(target=model.generate, kwargs=gen_kwargs, daemon=True).start()

    reply   = ""
    chatbot = list(chatbot or []) + [{"role": "assistant", "content": "⏳ (وضع CPU — قد يأخذ لحظات)…"}]
    history = list(history or []) + [{"role": "assistant", "content": ""}]

    try:
        for chunk in streamer:
            reply += chunk
            chatbot[-1] = {"role": "assistant", "content": reply}
            history[-1] = {"role": "assistant", "content": reply}
            yield chatbot, history
    except Exception as e:
        chatbot[-1]["content"] += f"\n\n⚠️ انقطع التوليد: {e}"
        yield chatbot, history


def _predict(chatbot, history):
    """
    المدخل الرئيسي للاستدلال.
    الأولوية: HF Inference API (سيرفرات HF البعيدة) ← GPU/CPU محلي
    @spaces.GPU مطلوبة على ZeroGPU hardware لكن الـ GPU يُستخدم فعلياً
    فقط عند فشل الـ API.
    """
    if USE_API:
        try:
            yield from _predict_api(chatbot, history)
            return
        except Exception as e:
            print(f"[Agent] API فشل ({e})، تحويل إلى التشغيل المحلي ({DEVICE})…")
            chatbot = list(chatbot or [])
            if chatbot and chatbot[-1].get("role") == "assistant":
                chatbot[-1]["content"] = f"⚠️ API غير متاح، أستخدم {DEVICE} محلياً…\n\n"
    yield from _predict_local(chatbot, history)


# @spaces.GPU مطلوبة على ZeroGPU hardware — بدونها يُقتل التطبيق
# الاستدلال الفعلي يذهب إلى HF API أولاً فلا يُستهلك GPU إلا كـ fallback
if HAS_SPACES:
    @spaces.GPU
    def predict(chatbot, history):
        yield from _predict(chatbot, history)
else:
    predict = _predict


# ── Message helpers ─────────────────────────────────────────────────────────

def add_text(chatbot, history, text):
    text = (text or "").strip()
    if not text:
        return chatbot, history, ""
    # Merge text into pending image/video turn (if any)
    if (history and history[-1].get("role") == "user"
            and isinstance(history[-1].get("content"), list)
            and not any(c.get("type") == "text" for c in history[-1]["content"])):
        new_content = list(history[-1]["content"]) + [{"type": "text", "text": text}]
        history  = list(history[:-1]) + [{"role": "user", "content": new_content}]
        chatbot  = list(chatbot  or []) + [{"role": "user", "content": text}]
    else:
        msg = {"role": "user", "content": text}
        chatbot = list(chatbot or []) + [msg]
        history = list(history or []) + [msg]
    return chatbot, history, ""


def add_file(chatbot, history, file):
    if file is None:
        return chatbot, history
    fname = (file.name or "").lower()
    if fname.endswith(IMAGE_EXTS):
        media_type, prompt = "image", (
            "قم بتحليل هذه الصورة بشكل كامل ومفصل. "
            "إذا كانت تحتوي على كود أو خطأ برمجي فحلّله بدقة. "
            "إذا كانت واجهة مستخدم فاقترح التحسينات. "
            "إذا كانت مخططاً فاشرحه بالتفصيل."
        )
    else:
        media_type, prompt = "video", "قم بوصف هذا الفيديو وتحليل محتواه البرمجي."
    chatbot_msg = {"role": "user", "content": (file.name,)}
    history_msg = {
        "role": "user",
        "content": [
            {"type": media_type, media_type: file.name},
            {"type": "text",     "text":      prompt},
        ],
    }
    return list(chatbot or []) + [chatbot_msg], list(history or []) + [history_msg]


def clear_history():
    return [], []


# ── GitHub helpers (Gradio callbacks) ──────────────────────────────────────

def connect_repo(token: str, repo_url: str, branch: str, proj_state: dict):
    """Connect to a GitHub repo and load its file tree."""
    if not repo_url.strip():
        return proj_state, "⚠️ أدخل رابط المستودع أولاً.", gr.update(choices=[])
    try:
        owner, repo = parse_github_url(repo_url)
        client = GitHubClient(token)
        info   = client.get_repo(owner, repo)
        branch = branch.strip() or info.get("default_branch", "main")
        tree   = client.get_tree(owner, repo, branch)
        files  = [
            item["path"] for item in tree
            if item["type"] == "blob"
            and not any(item["path"].startswith(x) for x in
                        (".git/", "node_modules/", "__pycache__/", ".venv/"))
        ]
        proj_state = {
            "owner":  owner, "repo":  repo,
            "branch": branch, "token": token,
            "files":  files,
            "loaded": {},   # path → (content, sha)
        }
        stars = info.get("stargazers_count", 0)
        lang  = info.get("language", "غير محدد")
        msg   = (f"✅ **{owner}/{repo}** — فرع: `{branch}`\n"
                 f"⭐ {stars} | لغة: {lang} | {len(files)} ملف")
        return proj_state, msg, gr.update(choices=sorted(files))
    except Exception as e:
        return proj_state, f"❌ {e}", gr.update(choices=[])


def load_file_into_chat(path: str, proj_state: dict, chatbot, history):
    """Read a file from GitHub and inject it as a user message."""
    if not path or not proj_state.get("owner"):
        return chatbot, history, "⚠️ اتصل بالمستودع أولاً."
    try:
        client  = GitHubClient(proj_state.get("token", ""))
        content, sha = client.get_file(
            proj_state["owner"], proj_state["repo"],
            path, proj_state["branch"]
        )
        proj_state["loaded"][path] = (content, sha)
        ext     = path.rsplit(".", 1)[-1] if "." in path else ""
        lang_map = {"py": "python", "js": "javascript", "ts": "typescript",
                    "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
                    "json": "json", "md": "markdown", "yml": "yaml", "yaml": "yaml",
                    "sh": "bash", "rs": "rust", "go": "go", "cpp": "cpp", "c": "c"}
        lang    = lang_map.get(ext, ext)
        text    = f"📄 محتوى الملف `{path}`:\n```{lang}\n{content}\n```"
        msg     = {"role": "user", "content": text}
        chatbot = list(chatbot or []) + [msg]
        history = list(history or []) + [msg]
        return chatbot, history, f"✅ تم تحميل `{path}` ({len(content.splitlines())} سطر)"
    except Exception as e:
        return chatbot, history, f"❌ {e}"


def push_file_to_github(
    file_path: str, new_content: str, commit_msg: str,
    proj_state: dict
):
    """Write/update a file in the repo via GitHub API."""
    if not proj_state.get("owner"):
        return "⚠️ اتصل بالمستودع أولاً."
    if not file_path.strip():
        return "⚠️ أدخل مسار الملف."
    if not proj_state.get("token"):
        return "⚠️ التوكن مطلوب للكتابة في المستودع."
    try:
        client = GitHubClient(proj_state["token"])
        # Get current SHA if file exists
        sha = None
        if file_path in proj_state.get("loaded", {}):
            _, sha = proj_state["loaded"][file_path]
        else:
            try:
                _, sha = client.get_file(
                    proj_state["owner"], proj_state["repo"],
                    file_path, proj_state["branch"]
                )
            except Exception:
                sha = None   # New file
        client.update_file(
            proj_state["owner"], proj_state["repo"],
            file_path, proj_state["branch"],
            commit_msg or f"تحديث {file_path} عبر مساعد البرمجة الذكي",
            new_content, sha
        )
        proj_state.get("loaded", {}).pop(file_path, None)   # Invalidate cache
        return f"✅ تم رفع `{file_path}` إلى `{proj_state['branch']}` بنجاح!"
    except Exception as e:
        return f"❌ فشل الرفع: {e}"


# ── UI ──────────────────────────────────────────────────────────────────────

CSS = """
body, .gradio-container { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }

/* Chat panel */
#chatbot { min-height: 560px; border-radius: 12px; }

/* Input area */
#query-row { align-items: flex-end; gap: 8px; }
#send-btn  { min-width: 90px; height: 48px; font-size: 1rem; border-radius: 10px; }

/* Sidebar */
#sidebar { background: #f8fafc; border-radius: 12px; padding: 12px; }
#repo-status { font-size: 0.85rem; border-radius: 8px; padding: 8px;
               background: #f0f9ff; border: 1px solid #bae6fd; }

/* Push panel */
#push-panel { background: #fefce8; border-radius: 10px; padding: 10px;
              border: 1px solid #fde047; }

footer { display: none !important; }
.gr-button-primary { background: #1e40af !important; }

/* Tip bar */
.tip-bar { text-align:center; color:#6b7280; font-size:0.83rem;
           margin-top:0.4rem; padding:0.3rem;
           background:#f9fafb; border-radius:8px; }
"""

with gr.Blocks(
    title="مساعد البرمجة الشخصي — Qwen3-VL",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=CSS,
) as demo:

    # ── Shared state ──────────────────────────────────────────────────────
    history_state = gr.State([])
    proj_state    = gr.State({})   # {owner, repo, branch, token, files, loaded}

    # ── Header ────────────────────────────────────────────────────────────
    gr.HTML("""
    <div style="text-align:center; padding:1.2rem 0 0.5rem;">
      <h1 style="font-size:2rem; margin:0; font-weight:700;">
        🤖 مساعد البرمجة الشخصي
      </h1>
      <p style="color:#4b5563; margin:0.3rem 0 0; font-size:0.95rem;">
        Powered by Qwen3-VL &nbsp;·&nbsp;
        تحليل الكود · قراءة المستودعات · رفع التعديلات · تحليل الصور
      </p>
    </div>
    """)

    # ── Main layout ───────────────────────────────────────────────────────
    with gr.Row():

        # ── Left sidebar ─────────────────────────────────────────────────
        with gr.Column(scale=1, elem_id="sidebar"):
            gr.Markdown("### 🔗 ربط المستودع")

            gh_token = gr.Textbox(
                label="GitHub Token",
                placeholder="ghp_xxxxxxxxxxxx",
                type="password",
                info="مطلوب للمستودعات الخاصة والرفع"
            )
            repo_url = gr.Textbox(
                label="رابط المستودع",
                placeholder="https://github.com/user/repo  أو  user/repo"
            )
            branch_box = gr.Textbox(
                label="الفرع (Branch)",
                placeholder="main",
                value="main"
            )
            connect_btn = gr.Button("🔌 اتصال بالمستودع", variant="primary")
            repo_status = gr.Markdown("", elem_id="repo-status")

            gr.Markdown("---")
            gr.Markdown("### 📂 تحميل ملف للمحادثة")
            file_picker = gr.Dropdown(
                label="اختر ملفاً من المستودع",
                choices=[],
                interactive=True
            )
            load_file_btn = gr.Button("📖 تحميل الملف")
            load_status   = gr.Markdown("")

            gr.Markdown("---")
            with gr.Group(elem_id="push-panel"):
                gr.Markdown("### 🚀 رفع تعديل إلى GitHub")
                push_path    = gr.Textbox(label="مسار الملف", placeholder="src/app.py")
                push_content = gr.Code(
                    label="محتوى الملف",
                    language="python",
                    lines=8,
                    interactive=True
                )
                push_msg     = gr.Textbox(
                    label="رسالة الـ Commit",
                    placeholder="إصلاح الخطأ في..."
                )
                push_btn     = gr.Button("⬆️ رفع إلى GitHub", variant="secondary")
                push_status  = gr.Markdown("")

        # ── Chat panel ───────────────────────────────────────────────────
        with gr.Column(scale=3):
            chatbot_ui = gr.Chatbot(
                value=[],
                label="المحادثة",
                height=560,
                type="messages",
                elem_id="chatbot",
                show_copy_button=True,
                bubble_full_width=False,
                render_markdown=True,
                latex_delimiters=[
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$",  "right": "$",  "display": False},
                ],
            )

            with gr.Row(elem_id="query-row"):
                query_box = gr.Textbox(
                    show_label=False,
                    placeholder="اكتب طلبك البرمجي… مثال: أنشئ تطبيق Flask بسيط | افحص هذا الكود | أصلح هذا الخطأ",
                    scale=6,
                    lines=2,
                    max_lines=6,
                    container=False,
                )
                send_btn = gr.Button("إرسال ▶", variant="primary", scale=1, elem_id="send-btn")

            with gr.Row():
                upload_btn = gr.UploadButton(
                    "📷 صورة / فيديو",
                    file_types=["image", "video"],
                    scale=2,
                )
                clear_btn = gr.Button("🗑️ مسح المحادثة", variant="secondary", scale=2)

            gr.HTML("""
            <div class="tip-bar">
              💡 اكتب طلبك البرمجي · ارفع صورة خطأ للتحليل · اربط مستودع GitHub لقراءة ورفع الملفات
            </div>
            """)

    # ── Event wiring ──────────────────────────────────────────────────────

    def _send(chatbot, history, text):
        return add_text(chatbot, history, text)

    # Text submit (Enter / button)
    query_box.submit(
        fn=_send,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(predict, [chatbot_ui, history_state], [chatbot_ui, history_state])

    send_btn.click(
        fn=_send,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(predict, [chatbot_ui, history_state], [chatbot_ui, history_state])

    # File upload → auto-analyze
    upload_btn.upload(
        fn=add_file,
        inputs=[chatbot_ui, history_state, upload_btn],
        outputs=[chatbot_ui, history_state],
    ).then(predict, [chatbot_ui, history_state], [chatbot_ui, history_state])

    # GitHub: connect repo
    connect_btn.click(
        fn=connect_repo,
        inputs=[gh_token, repo_url, branch_box, proj_state],
        outputs=[proj_state, repo_status, file_picker],
    )

    # GitHub: load file into chat
    load_file_btn.click(
        fn=load_file_into_chat,
        inputs=[file_picker, proj_state, chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state, load_status],
    )

    # GitHub: push file
    push_btn.click(
        fn=push_file_to_github,
        inputs=[push_path, push_content, push_msg, proj_state],
        outputs=[push_status],
    )

    # Clear
    clear_btn.click(fn=clear_history, outputs=[chatbot_ui, history_state])


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    load_model_once()
    demo.queue(max_size=10).launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        share=False,
    )


if __name__ == "__main__":
    main()
