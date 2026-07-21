import os
import copy
from threading import Thread
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

model = None
processor = None

def _load_model_processor():
    checkpoint = 'Qwen/Qwen3-VL-2B-Instruct'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    p = AutoProcessor.from_pretrained(checkpoint, trust_remote_code=True)
    m = AutoModelForImageTextToText.from_pretrained(
        checkpoint, device_map='auto', trust_remote_code=True,
        torch_dtype=torch.bfloat16 if device == 'cuda' else torch.float32
    )
    return m, p

def add_text(chatbot, history, text):
    if not text: return chatbot, history, ""
    msg = {'role': 'user', 'content': text}
    return (chatbot or []) + [msg], (history or []) + [msg], ""

def add_file(chatbot, history, file):
    if file is None: return chatbot, history
    mime = 'image' if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'video'
    msg = {'role': 'user', 'content': [{'type': mime, mime: file.name}]}
    return (chatbot or []) + [msg], (history or []) + [msg]

def predict(chatbot, history):
    global model, processor
    if model is None: model, processor = _load_model_processor()
    
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
    gr.Markdown("# Qwen3-VL Optimized Demo")
    chatbot = gr.Chatbot(label='Assistant', height=600) # Fixed: No type='messages'
    with gr.Row():
        query = gr.Textbox(show_label=False, placeholder='Type message...', scale=4)
        addfile_btn = gr.UploadButton('📁', file_types=['image', 'video'])
    
    task_history = gr.State([])

    query.submit(add_text, [chatbot, task_history, query], [chatbot, task_history, query]).then(
        predict, [chatbot, task_history], [chatbot]
    )
    addfile_btn.upload(add_file, [chatbot, task_history, addfile_btn], [chatbot, task_history])

if __name__ == '__main__':
    model, processor = _load_model_processor()
    demo.queue().launch()
