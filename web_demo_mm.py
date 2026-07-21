import os
import copy
from threading import Thread
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

# متغيرات عالمية لتجنب مشاكل gr.State
model = None
processor = None

def load_model():
    global model, processor
    checkpoint = 'Qwen/Qwen3-VL-2B-Instruct'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    processor = AutoProcessor.from_pretrained(checkpoint, trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        checkpoint, 
        device_map='auto', 
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if device == 'cuda' else torch.float32
    )

def add_text(chatbot, history, text):
    if not text: return chatbot, history, ""
    msg = {'role': 'user', 'content': text}
    chatbot = (chatbot or []) + [msg]
    history = (history or []) + [msg]
    return chatbot, history, ""

def add_file(chatbot, history, file):
    if file is None: return chatbot, history
    mime = 'image' if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) else 'video'
    msg = {'role': 'user', 'content': [{'type': mime, mime: file.name}]}
    chatbot = (chatbot or []) + [msg]
    history = (history or []) + [msg]
    return chatbot, history

def predict(chatbot, history):
    global model, processor
    if model is None: load_model()
    
    text = processor.apply_chat_template(history, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(history)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors='pt').to(model.device)
    
    streamer = TextIteratorStreamer(processor, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(inputs, streamer=streamer, max_new_tokens=1024)
    
    thread = Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()
    
    chatbot.append({'role': 'assistant', 'content': ''})
    history.append({'role': 'assistant', 'content': ''})
    
    for new_text in streamer:
        chatbot[-1]['content'] += new_text
        history[-1]['content'] += new_text
        yield chatbot

with gr.Blocks() as demo:
    gr.Markdown("# Qwen3-VL Fixed Demo (Gradio 6)")
    chatbot = gr.Chatbot(label='Assistant', height=600)
    with gr.Row():
        query = gr.Textbox(show_label=False, placeholder='Type here...', scale=4)
        upload_btn = gr.UploadButton('📁', file_types=['image', 'video'])
    
    history_state = gr.State([])

    query.submit(add_text, [chatbot, history_state, query], [chatbot, history_state, query]).then(
        predict, [chatbot, history_state], [chatbot]
    )
    upload_btn.upload(add_file, [chatbot, history_state, upload_btn], [chatbot, history_state])

if __name__ == '__main__':
    load_model()
    demo.queue().launch()
