import os
import copy
from argparse import ArgumentParser
from threading import Thread
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer
from qwen_vl_utils import process_vision_info

model = None
processor = None
backend = None

def _get_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--checkpoint-path', type=str, default='Qwen/Qwen3-VL-2B-Instruct')
    parser.add_argument('--cpu-only', action='store_true')
    parser.add_argument('--flash-attn2', action='store_true', default=False)
    parser.add_argument('--share', action='store_true', default=False)
    parser.add_argument('--server-port', type=int, default=7860)
    parser.add_argument('--server-name', type=str, default='127.0.0.1')
    parser.add_argument('--backend', type=str, default='hf', choices=['vllm', 'hf'])
    return parser.parse_args()

def _load_model_processor(args):
    device = 'cpu' if args.cpu_only else 'cuda'
    p = AutoProcessor.from_pretrained(args.checkpoint_path, trust_remote_code=True)
    m = AutoModelForImageTextToText.from_pretrained(
        args.checkpoint_path, device_map=device, trust_remote_code=True,
        torch_dtype=torch.bfloat16 if not args.cpu_only else torch.float32,
        attn_implementation='flash_attention_2' if args.flash_attn2 else None
    )
    return m, p, args.backend

def add_text(chatbot, history, text):
    if not text:
        return chatbot, history, ""
    msg = {'role': 'user', 'content': text}
    chatbot = (chatbot or []) + [msg]
    history = (history or []) + [msg]
    return chatbot, history, ""

def add_file(chatbot, history, file):
    if file is None:
        return chatbot, history
    mime = 'image' if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) else 'video'
    msg = {'role': 'user', 'content': [{'type': mime, mime: file.name}]}
    chatbot = (chatbot or []) + [msg]
    history = (history or []) + [msg]
    return chatbot, history

def reset_state():
    return [], []

def predict(chatbot, history):
    global model, processor, backend
    messages = copy.deepcopy(history)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors='pt').to(model.device)
    streamer = TextIteratorStreamer(processor, skip_prompt=True, skip_special_tokens=True)
    generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=2048)
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    chatbot.append({'role': 'assistant', 'content': ''})
    history.append({'role': 'assistant', 'content': ''})
    for new_text in streamer:
        chatbot[-1]['content'] += new_text
        history[-1]['content'] += new_text
        yield chatbot

def _launch_demo(args, _model, _processor, _backend):
    global model, processor, backend
    model, processor, backend = _model, _processor, _backend
    with gr.Blocks() as demo:
        gr.Markdown("# Qwen3-VL Gradio 6.2.0 Demo")
        chatbot = gr.Chatbot(label='Qwen3-VL', height=500)
        query = gr.Textbox(lines=2, label='Input', placeholder='Type and press Enter')
        task_history = gr.State([])
        with gr.Row():
            addfile_btn = gr.UploadButton('📁 Upload', file_types=['image', 'video'])
            submit_btn = gr.Button('🚀 Submit')
            empty_bin = gr.Button('🧹 Clear')
        submit_btn.click(add_text, [chatbot, task_history, query], [chatbot, task_history, query]).then(predict, [chatbot, task_history], [chatbot])
        query.submit(add_text, [chatbot, task_history, query], [chatbot, task_history, query]).then(predict, [chatbot, task_history], [chatbot])
        addfile_btn.upload(add_file, [chatbot, task_history, addfile_btn], [chatbot, task_history])
        empty_bin.click(reset_state, None, [chatbot, task_history])
    demo.queue().launch(share=args.share, server_name=args.server_name, server_port=args.server_port)

if __name__ == '__main__':
    args = _get_args()
    m, p, b = _load_model_processor(args)
    _launch_demo(args, m, p, b)