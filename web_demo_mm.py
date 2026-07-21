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
    load_kwargs = dict(
        trust_remote_code=True,
        dtype=dtype,
    )
    if DEVICE == 'cuda':
        load_kwargs['device_map'] = 'auto'
    model = AutoModelForImageTextToText.from_pretrained(CHECKPOINT, **load_kwargs)
    if DEVICE == 'cpu':
        model = model.to('cpu')
    model.eval()
    print("[الدكتور الذكي] تم تحميل النموذج بنجاح!")


def _predict(chatbot, history):
    load_model_once()

    # Build messages with system prompt
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

    chatbot = list(chatbot or [])
    chatbot.append({'role': 'assistant', 'content': ''})
    history = list(history or [])
    history.append({'role': 'assistant', 'content': ''})

    for new_text in streamer:
        chatbot[-1]['content'] += new_text
        history[-1]['content'] += new_text
        yield chatbot, history


if HAS_SPACES:
    @spaces.GPU
    def predict(chatbot, history):
        yield from _predict(chatbot, history)
else:
    predict = _predict


def add_text(chatbot, history, text):
    if not text or not text.strip():
        return chatbot, history, ""
    msg = {'role': 'user', 'content': text.strip()}
    chatbot = list(chatbot or []) + [msg]
    history = list(history or []) + [msg]
    return chatbot, history, ""


def add_file(chatbot, history, file):
    if file is None:
        return chatbot, history
    fname = file.name.lower()
    if fname.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
        content = [{'type': 'image', 'image': file.name}]
    else:
        content = [{'type': 'video', 'video': file.name}]
    msg = {'role': 'user', 'content': content}
    chatbot = list(chatbot or []) + [msg]
    history = list(history or []) + [msg]
    return chatbot, history


def clear_history():
    return [], []


CSS = """
body { direction: rtl; }
#chatbot { direction: rtl; }
.gr-textbox textarea { direction: rtl; text-align: right; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="الدكتور الذكي - Qwen3-VL",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
    ),
    css=CSS,
) as demo:
    gr.Markdown("""
<div style="text-align:center; padding: 1rem;">
<h1 style="font-size:2rem;">🎓 الدكتور الذكي</h1>
<p style="color:#666; font-size:1.1rem;">
أستاذك الجامعي الذكي — تحليل الصور · قراءة رموز QR · استخراج النصوص · شرح المفاهيم
</p>
<p style="color:#999; font-size:0.9rem;">
Powered by Qwen3-VL-2B-Instruct
</p>
</div>
""")

    chatbot_ui = gr.Chatbot(
        label='المحادثة',
        height=520,
        type='messages',
        elem_id='chatbot',
        avatar_images=(None, "https://huggingface.co/front/assets/huggingface_logo.svg"),
        show_copy_button=True,
    )

    with gr.Row():
        query_box = gr.Textbox(
            show_label=False,
            placeholder='اكتب سؤالك هنا... / Type your question here...',
            scale=5,
            lines=2,
            max_lines=6,
        )
        with gr.Column(scale=1, min_width=120):
            upload_btn = gr.UploadButton('📷 رفع صورة', file_types=['image', 'video'])
            clear_btn = gr.Button('🗑️ مسح الكل', variant='secondary')

    history_state = gr.State([])

    # Submit on Enter
    query_box.submit(
        fn=add_text,
        inputs=[chatbot_ui, history_state, query_box],
        outputs=[chatbot_ui, history_state, query_box],
    ).then(
        fn=predict,
        inputs=[chatbot_ui, history_state],
        outputs=[chatbot_ui, history_state],
    )

    # Upload image/video then auto-prompt
    upload_btn.upload(
        fn=add_file,
        inputs=[chatbot_ui, history_state, upload_btn],
        outputs=[chatbot_ui, history_state],
    )

    clear_btn.click(
        fn=clear_history,
        inputs=[],
        outputs=[chatbot_ui, history_state],
    )

    gr.Markdown("""
<div style="text-align:center; color:#aaa; font-size:0.8rem; margin-top:1rem;">
💡 <b>نصيحة:</b> ارفع صورة ثم اكتب سؤالك عنها | Upload an image then type your question about it
</div>
""")


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
