import os
import torch
import gradio as gr
from threading import Thread
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

# ZeroGPU support - optional
try:
    import spaces
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False

CHECKPOINT = os.environ.get('MODEL_CHECKPOINT', 'Qwen/Qwen3-VL-2B-Instruct')
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

SYSTEM_PROMPT = """أنت الدكتور الذكي، أستاذ جامعي متخصص ومساعد أكاديمي بارع. تتميز بالقدرات التالية:
- تحليل الصور والمخططات العلمية والرسوم البيانية بدقة عالية
- قراءة رموز QR واستخراج محتواها الكامل
- استخراج النصوص من الصور والوثائق والمستندات المصورة
- شرح المفاهيم الأكاديمية المعقدة بأسلوب واضح ومنهجي
- الإجابة باللغة التي يتحدث بها الطالب (العربية أو الإنجليزية)
- تقديم أمثلة توضيحية وشرح خطوة بخطوة
- تصحيح المفاهيم الخاطئة بلطف واحترام
كن دقيقاً، علمياً، ومشجعاً في جميع ردودك."""

model = None
processor = None


def load_model_once():
    global model, processor
    if model is not None:
        return
    print(f"[الدكتور الذكي] جاري تحميل النموذج {CHECKPOINT} على {DEVICE}...")
    processor = AutoProcessor.from_pretrained(CHECKPOINT, trust_remote_code=True)
    dtype = torch.bfloat16 if DEVICE == 'cuda' else torch.float32
    load_kwargs = dict(trust_remote_code=True, dtype=dtype)
    if DEVICE == 'cuda':
        load_kwargs['device_map'] = 'auto'
    model = AutoModelForImageTextToText.from_pretrained(CHECKPOINT, **load_kwargs)
    if DEVICE == 'cpu':
        model = model.to('cpu')
    model.eval()
    print("[الدكتور الذكي] تم تحميل النموذج بنجاح!")


def _predict(chatbot, history):
    """Run inference and stream tokens."""
    load_model_once()

    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + list(history or [])

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors='pt',
    ).to(model.device)

    streamer = TextIteratorStreamer(processor, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(**inputs, streamer=streamer, max_new_tokens=1024)

    thread = Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()

    # Append empty assistant turn that we'll fill token-by-token
    new_assistant = {'role': 'assistant', 'content': ''}
    chatbot = list(chatbot or []) + [new_assistant.copy()]
    history = list(history or []) + [new_assistant.copy()]

    for new_text in streamer:
        chatbot[-1]['content'] += new_text
        history[-1]['content'] += new_text
        yield chatbot, history

    thread.join()


if HAS_SPACES:
    @spaces.GPU
    def predict(chatbot, history):
        yield from _predict(chatbot, history)
else:
    predict = _predict


# ── helpers ────────────────────────────────────────────────────────────────

def add_text(chatbot, history, text):
    """Merge typed text into the last user turn (so image + text stay together)."""
    text = (text or '').strip()
    if not text:
        return chatbot, history, ""

    # If the last history entry is a user image-only turn, append text to it
    if (history
            and history[-1].get('role') == 'user'
            and isinstance(history[-1].get('content'), list)
            and not any(c.get('type') == 'text' for c in history[-1]['content'])):
        new_content = list(history[-1]['content']) + [{'type': 'text', 'text': text}]
        merged = {'role': 'user', 'content': new_content}
        chatbot = list(chatbot[:-1]) + [merged]
        history = list(history[:-1]) + [merged]
    else:
        msg = {'role': 'user', 'content': text}
        chatbot = list(chatbot or []) + [msg]
        history = list(history or []) + [msg]

    return chatbot, history, ""


def add_file(chatbot, history, file):
    """Add an image/video with a default Arabic analysis prompt."""
    if file is None:
        return chatbot, history

    fname = (file.name or '').lower()
    if fname.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
        content = [
            {'type': 'image', 'image': file.name},
            {'type': 'text', 'text':
                'قم بتحليل هذه الصورة بشكل كامل ومفصل. '
                'إذا كانت تحتوي على رمز QR فاستخرج محتواه كاملاً. '
                'إذا كانت تحتوي على نصوص فاستخرجها كلها. '
                'إذا كانت صورة علمية أو أكاديمية فاشرحها بالتفصيل.'},
        ]
    else:
        content = [
            {'type': 'video', 'video': file.name},
            {'type': 'text', 'text': 'قم بوصف هذا الفيديو وتحليل محتواه.'},
        ]

    msg = {'role': 'user', 'content': content}
    chatbot = list(chatbot or []) + [msg]
    history = list(history or []) + [msg]
    return chatbot, history


def clear_history():
    return [], []


# ── UI ─────────────────────────────────────────────────────────────────────

CSS = """
body, .gradio-container { direction: rtl; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }
#chatbot { min-height: 460px; }
#query-row { align-items: flex-end; gap: 8px; }
#send-btn { min-width: 90px; height: 48px; font-size: 1rem; }
#upload-btn { min-width: 120px; }
footer { display: none !important; }
.gr-button-primary { background: #1e40af !important; }
"""

with gr.Blocks(
    title="الدكتور الذكي — Qwen3-VL",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=CSS,
) as demo:

    gr.HTML("""
    <div style="text-align:center; padding:1.2rem 0 0.5rem;">
      <h1 style="font-size:2rem; margin:0;">🎓 الدكتور الذكي</h1>
      <p style="color:#555; margin:0.3rem 0 0;">
        أستاذك الجامعي الذكي — تحليل الصور · قراءة QR · استخراج النصوص · شرح المفاهيم
      </p>
    </div>
    """)

    chatbot_ui = gr.Chatbot(
        value=[],
        label='المحادثة',
        height=480,
        type='messages',
        elem_id='chatbot',
        show_copy_button=True,
        bubble_full_width=False,
    )

    with gr.Row(elem_id='query-row'):
        query_box = gr.Textbox(
            show_label=False,
            placeholder='اكتب سؤالك هنا ثم اضغط إرسال أو Enter…',
            scale=6,
            lines=2,
            max_lines=5,
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
        clear_btn = gr.Button('🗑️ مسح المحادثة', variant='secondary', scale=2)

    gr.HTML("""
    <div style="text-align:center; color:#999; font-size:0.82rem; margin-top:0.5rem;">
      💡 ارفع صورة وسيتم تحليلها تلقائياً، أو اكتب سؤالك ثم اضغط <b>إرسال</b>
    </div>
    """)

    history_state = gr.State([])

    # ── wire events ─────────────────────────────────────────────────────────

    def _submit_chain(chatbot, history, text):
        """add_text then predict — used by both Enter and button."""
        return add_text(chatbot, history, text)

    # Enter key submit
    query_box.submit(
        fn=add_text,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(
        fn=predict,
        inputs=[chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state],
    )

    # Send button click
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
    demo.queue(max_size=5).launch(
        server_name='0.0.0.0',
        server_port=7860,
        show_error=True,
        share=False,
    )


if __name__ == '__main__':
    main()
