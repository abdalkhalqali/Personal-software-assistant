import os
import traceback
import torch
import gradio as gr
from threading import Thread
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

# ── ZeroGPU support ────────────────────────────────────────────────────────
try:
    import spaces
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False

# ── Config ─────────────────────────────────────────────────────────────────
CHECKPOINT    = os.environ.get('MODEL_CHECKPOINT', 'Qwen/Qwen3-VL-2B-Instruct')
DEVICE        = 'cuda' if torch.cuda.is_available() else 'cpu'
MAX_NEW_TOKENS = int(os.environ.get('MAX_NEW_TOKENS', '2048'))

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.avif')
VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v')

SYSTEM_PROMPT = """أنت الدكتور الذكي، أستاذ جامعي متخصص ومساعد أكاديمي بارع. تتميز بالقدرات التالية:
- تحليل الصور والمخططات العلمية والرسوم البيانية بدقة عالية
- قراءة رموز QR واستخراج محتواها الكامل
- استخراج النصوص من الصور والوثائق والمستندات المصورة
- شرح المفاهيم الأكاديمية المعقدة بأسلوب واضح ومنهجي
- الإجابة باللغة التي يتحدث بها الطالب (العربية أو الإنجليزية)
- تقديم أمثلة توضيحية وشرح خطوة بخطوة
- تصحيح المفاهيم الخاطئة بلطف واحترام
كن دقيقاً، علمياً، ومشجعاً في جميع ردودك. لا تختصر إجاباتك إلا إذا طُلب منك ذلك."""

# ── Model singleton ────────────────────────────────────────────────────────
model = None
processor = None


def load_model_once():
    global model, processor
    if model is not None:
        return

    print(f"[الدكتور الذكي] جاري تحميل النموذج {CHECKPOINT} على {DEVICE}...")
    processor = AutoProcessor.from_pretrained(CHECKPOINT, trust_remote_code=True)

    dtype = torch.bfloat16 if DEVICE == 'cuda' else torch.float32
    load_kwargs = dict(trust_remote_code=True, torch_dtype=dtype)

    if DEVICE == 'cuda':
        load_kwargs['device_map'] = 'auto'
        # Enable flash-attention 2 if available (much faster on GPU)
        try:
            load_kwargs['attn_implementation'] = 'flash_attention_2'
        except Exception:
            pass
    else:
        load_kwargs['device_map'] = 'cpu'

    model = AutoModelForImageTextToText.from_pretrained(CHECKPOINT, **load_kwargs)
    model.eval()
    print("[الدكتور الذكي] تم تحميل النموذج بنجاح!")


# ── Inference ──────────────────────────────────────────────────────────────

def _predict(chatbot, history):
    """
    Run inference using `history` (Qwen message format) and stream tokens.
    `chatbot` is the Gradio display state; `history` is the model input state.
    Both are updated and yielded together.
    """
    load_model_once()

    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + list(history or [])

    # ── Build inputs ─────────────────────────────────────────────────────
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
            return_tensors='pt',
        ).to(model.device if hasattr(model, 'device') else DEVICE)
    except Exception as e:
        err = f'⚠️ خطأ في معالجة الإدخال:\n```\n{traceback.format_exc()}\n```'
        chatbot = list(chatbot or []) + [{'role': 'assistant', 'content': err}]
        yield chatbot, history
        return

    # ── Stream generation ─────────────────────────────────────────────────
    streamer = TextIteratorStreamer(
        processor, skip_prompt=True, skip_special_tokens=True
    )
    gen_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,          # greedy — fastest & most deterministic
        temperature=None,
        top_p=None,
        repetition_penalty=1.05,  # mild penalty to avoid repetition loops
    )

    thread = Thread(target=model.generate, kwargs=gen_kwargs, daemon=True)
    thread.start()

    # Append empty assistant turn
    assistant_reply = ''
    chatbot  = list(chatbot  or []) + [{'role': 'assistant', 'content': ''}]
    history  = list(history  or []) + [{'role': 'assistant', 'content': ''}]

    try:
        for chunk in streamer:
            assistant_reply += chunk
            chatbot[-1]  = {'role': 'assistant', 'content': assistant_reply}
            history[-1]  = {'role': 'assistant', 'content': assistant_reply}
            yield chatbot, history
    except Exception as e:
        chatbot[-1]['content'] += f'\n\n⚠️ انقطع التوليد: {e}'
        yield chatbot, history

    thread.join()


if HAS_SPACES:
    @spaces.GPU
    def predict(chatbot, history):
        yield from _predict(chatbot, history)
else:
    predict = _predict


# ── Message helpers ─────────────────────────────────────────────────────────
#
# IMPORTANT: `chatbot` uses Gradio-5 display format; `history` uses the Qwen
# multimodal message format. They MUST be kept separate to avoid the
# `FileMessage.alt_text` validation error that occurs when a content-list
# entry (dict) is misidentified as the alt_text string of a FileMessage.
#
#   chatbot entry for an image → {'role': 'user', 'content': (file_path,)}
#   history entry for an image → {'role': 'user', 'content':
#       [{'type': 'image', 'image': path}, {'type': 'text', 'text': prompt}]}

def _media_prompt(fname: str) -> tuple[str, str]:
    """Return (media_type, auto-prompt) for a given filename."""
    lo = fname.lower()
    if lo.endswith(IMAGE_EXTS):
        return 'image', (
            'قم بتحليل هذه الصورة بشكل كامل ومفصل. '
            'إذا كانت تحتوي على رمز QR فاستخرج محتواه كاملاً. '
            'إذا كانت تحتوي على نصوص فاستخرجها كلها. '
            'إذا كانت صورة علمية أو أكاديمية فاشرحها بالتفصيل.'
        )
    return 'video', 'قم بوصف هذا الفيديو وتحليل محتواه بالتفصيل.'


def add_file(chatbot, history, file):
    """Upload an image/video → display in chatbot + queue in history for inference."""
    if file is None:
        return chatbot, history

    media_type, auto_prompt = _media_prompt(file.name or '')

    # Gradio-5 display format: tuple triggers file/image rendering
    chatbot_msg = {'role': 'user', 'content': (file.name,)}

    # Qwen multimodal message format for the model
    history_msg = {
        'role': 'user',
        'content': [
            {'type': media_type, media_type: file.name},
            {'type': 'text',    'text':       auto_prompt},
        ],
    }

    chatbot = list(chatbot or []) + [chatbot_msg]
    history = list(history or []) + [history_msg]
    return chatbot, history


def add_text(chatbot, history, text):
    """Append user text, merging into a pending image turn if present."""
    text = (text or '').strip()
    if not text:
        return chatbot, history, ""

    # If the latest history turn is a user multimodal turn without any text
    # content yet, append the user's typed text to it instead of starting a
    # new turn.  This lets the user type a custom question for an uploaded image.
    if (
        history
        and history[-1].get('role') == 'user'
        and isinstance(history[-1].get('content'), list)
        and not any(c.get('type') == 'text' for c in history[-1]['content'])
    ):
        new_content = list(history[-1]['content']) + [{'type': 'text', 'text': text}]
        history = list(history[:-1]) + [{'role': 'user', 'content': new_content}]
        # Chatbot already shows the image; add the text as a separate display entry
        chatbot = list(chatbot or []) + [{'role': 'user', 'content': text}]
    else:
        msg = {'role': 'user', 'content': text}
        chatbot = list(chatbot or []) + [msg]
        history = list(history or []) + [msg]

    return chatbot, history, ""


def clear_history():
    return [], []


# ── UI ──────────────────────────────────────────────────────────────────────

CSS = """
/* RTL base */
body, .gradio-container {
    direction: rtl;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
}

/* Chatbot panel */
#chatbot {
    min-height: 520px;
    border-radius: 12px;
}

/* Input row */
#query-row { align-items: flex-end; gap: 8px; }
#send-btn  { min-width: 90px; height: 48px; font-size: 1rem; border-radius: 10px; }
#upload-btn { min-width: 140px; border-radius: 10px; }
#clear-btn  { border-radius: 10px; }

/* Hide Gradio footer */
footer { display: none !important; }

/* Primary colour override */
.gr-button-primary { background: #1e40af !important; }

/* Tip bar */
.tip-bar {
    text-align: center;
    color: #6b7280;
    font-size: 0.83rem;
    margin-top: 0.4rem;
    padding: 0.3rem;
    background: #f9fafb;
    border-radius: 8px;
}
"""

with gr.Blocks(
    title="الدكتور الذكي — Qwen3-VL",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=CSS,
) as demo:

    gr.HTML("""
    <div style="text-align:center; padding:1.4rem 0 0.6rem;">
      <h1 style="font-size:2.1rem; margin:0; font-weight:700;">🎓 الدكتور الذكي</h1>
      <p style="color:#4b5563; margin:0.35rem 0 0; font-size:1rem;">
        أستاذك الجامعي الذكي &nbsp;·&nbsp; تحليل الصور &nbsp;·&nbsp; قراءة QR &nbsp;·&nbsp; استخراج النصوص &nbsp;·&nbsp; شرح المفاهيم
      </p>
    </div>
    """)

    chatbot_ui = gr.Chatbot(
        value=[],
        label='المحادثة',
        height=520,
        type='messages',
        elem_id='chatbot',
        show_copy_button=True,
        bubble_full_width=False,
        render_markdown=True,
        latex_delimiters=[
            {'left': '$$', 'right': '$$', 'display': True},
            {'left': '$',  'right': '$',  'display': False},
        ],
    )

    with gr.Row(elem_id='query-row'):
        query_box = gr.Textbox(
            show_label=False,
            placeholder='اكتب سؤالك هنا ثم اضغط إرسال أو Enter…',
            scale=6,
            lines=2,
            max_lines=6,
            container=False,
        )
        send_btn = gr.Button('إرسال ▶', variant='primary', scale=1, elem_id='send-btn')

    with gr.Row():
        upload_btn = gr.UploadButton(
            '📷 ارفع صورة أو فيديو',
            file_types=['image', 'video'],
            scale=3,
            elem_id='upload-btn',
        )
        clear_btn = gr.Button(
            '🗑️ مسح المحادثة', variant='secondary', scale=2, elem_id='clear-btn'
        )

    gr.HTML("""
    <div class="tip-bar">
      💡 ارفع صورة لتحليلها تلقائياً، أو اكتب سؤالك ثم اضغط <b>إرسال</b>.
      &nbsp;|&nbsp; يدعم الصور · الفيديو · رموز QR · المعادلات الرياضية (LaTeX)
    </div>
    """)

    history_state = gr.State([])

    # ── Event wiring ─────────────────────────────────────────────────────────

    # Enter key
    query_box.submit(
        fn=add_text,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(
        fn=predict,
        inputs=[chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state],
    )

    # Send button
    send_btn.click(
        fn=add_text,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(
        fn=predict,
        inputs=[chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state],
    )

    # Image/video upload → auto-analyze immediately
    upload_btn.upload(
        fn=add_file,
        inputs=[chatbot_ui, history_state, upload_btn],
        outputs=[chatbot_ui, history_state],
    ).then(
        fn=predict,
        inputs=[chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state],
    )

    # Clear
    clear_btn.click(
        fn=clear_history,
        inputs=[],
        outputs=[chatbot_ui, history_state],
    )


def main():
    load_model_once()
    demo.queue(max_size=10).launch(
        server_name='0.0.0.0',
        server_port=7860,
        show_error=True,
        share=False,
    )


if __name__ == '__main__':
    main()
