# Copyright (c) Alibaba Cloud.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import spaces

import os
import copy
import re
from argparse import ArgumentParser
from threading import Thread

import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, TextIteratorStreamer


def _get_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--checkpoint-path', type=str, default='Qwen/Qwen2-VL-2B-Instruct', help='Checkpoint name or path')
    parser.add_argument('--cpu-only', action='store_true', help='Run demo with CPU only')
    parser.add_argument('--flash-attn2', action='store_true', default=False, help='Enable flash_attention_2')
    parser.add_argument('--share', action='store_true', default=False, help='Create a publicly shareable link')
    parser.add_argument('--inbrowser', action='store_true', default=False, help='Launch in browser')
    parser.add_argument('--server-port', type=int, default=7860, help='Demo server port')
    parser.add_argument('--server-name', type=str, default='0.0.0.0', help='Demo server name')
    parser.add_argument('--backend', type=str, choices=['hf', 'vllm'], default='hf', help='Backend to use')
    parser.add_argument('--gpu-memory-utilization', type=float, default=0.70, help='GPU memory utilization')
    parser.add_argument('--tensor-parallel-size', type=int, default=None, help='Tensor parallel size')
    args = parser.parse_args()
    return args


def _load_model_processor(args):
    if args.cpu_only:
        device_map = 'cpu'
    else:
        device_map = 'auto'
    
    if args.flash_attn2:
        model = AutoModelForImageTextToText.from_pretrained(
            args.checkpoint_path,
            torch_dtype=torch.float16,
            attn_implementation='flash_attention_2',
            device_map=device_map,
            low_cpu_mem_usage=True
        )
    else:
        model = AutoModelForImageTextToText.from_pretrained(
            args.checkpoint_path,
            torch_dtype=torch.float16,
            device_map=device_map,
            low_cpu_mem_usage=True
        )
    processor = AutoProcessor.from_pretrained(args.checkpoint_path)
    return model, processor, 'hf'


def _parse_text(text):
    lines = text.split('\n')
    lines = [line for line in lines if line != '']
    count = 0
    for i, line in enumerate(lines):
        if '```' in line:
            count += 1
            items = line.split('`')
            if count % 2 == 1:
                lines[i] = f'<pre><code class="language-{items[-1]}">'
            else:
                lines[i] = '<br></code></pre>'
        else:
            if i > 0:
                if count % 2 == 1:
                    line = line.replace('`', r'\`')
                    line = line.replace('<', '&lt;')
                    line = line.replace('>', '&gt;')
                    line = line.replace(' ', '&nbsp;')
                    line = line.replace('*', '&ast;')
                    line = line.replace('_', '&lowbar;')
                    line = line.replace('-', '&#45;')
                    line = line.replace('.', '&#46;')
                    line = line.replace('!', '&#33;')
                    line = line.replace('(', '&#40;')
                    line = line.replace(')', '&#41;')
                    line = line.replace('$', '&#36;')
                lines[i] = '<br>' + line
    text = ''.join(lines)
    return text


def _remove_image_special(text):
    text = text.replace('<ref>', '').replace('</ref>', '')
    return re.sub(r'<box>.*?(</box>|$)', '', text)


def _is_video_file(filename):
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.mpeg']
    return any(filename.lower().endswith(ext) for ext in video_extensions)


def _gc():
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _transform_messages(original_messages):
    transformed_messages = []
    for message in original_messages:
        new_content = []
        for item in message['content']:
            if 'image' in item:
                new_item = {'type': 'image', 'image': item['image']}
            elif 'text' in item:
                new_item = {'type': 'text', 'text': item['text']}
            elif 'video' in item:
                new_item = {'type': 'video', 'video': item['video']}
            else:
                continue
            new_content.append(new_item)
        new_message = {'role': message['role'], 'content': new_content}
        transformed_messages.append(new_message)
    return transformed_messages


def _launch_demo(args, model, processor, backend):
    def call_local_model(model, processor, messages, backend):
        messages = _transform_messages(messages)
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        tokenizer = processor.tokenizer
        streamer = TextIteratorStreamer(tokenizer, timeout=20.0, skip_prompt=True, skip_special_tokens=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        gen_kwargs = {'max_new_tokens': 256, 'streamer': streamer, **inputs}
        thread = Thread(target=model.generate, kwargs=gen_kwargs)
        thread.start()
        generated_text = ''
        for new_text in streamer:
            generated_text += new_text
            yield generated_text

    def create_predict_fn():
        def predict(_chatbot, task_history):
            nonlocal model, processor, backend
            
            if not _chatbot or len(_chatbot) == 0:
                return _chatbot
            
            last_msg = _chatbot[-1]
            if isinstance(last_msg, tuple) and len(last_msg) > 0:
                chat_query = last_msg[0] if last_msg[0] else ''
            else:
                chat_query = str(last_msg) if last_msg else ''
            
            if len(task_history) > 0:
                query = task_history[-1][0] if isinstance(task_history[-1], (tuple, list)) else str(task_history[-1])
            else:
                query = chat_query
            
            if not chat_query or len(str(chat_query).strip()) == 0:
                _chatbot.pop() if _chatbot else None
                if task_history and len(task_history) > 0:
                    task_history.pop()
                return _chatbot
            
            print('User: ' + _parse_text(str(query)))
            history_cp = copy.deepcopy(task_history)
            full_response = ''
            messages = []
            content = []
            
            for item in history_cp:
                if isinstance(item, tuple) and len(item) >= 2:
                    q, a = item[0], item[1]
                    if isinstance(q, (tuple, list)):
                        if len(q) > 0 and _is_video_file(str(q[0])):
                            content.append({'video': os.path.abspath(str(q[0]))})
                        elif len(q) > 0:
                            content.append({'image': os.path.abspath(str(q[0]))})
                    else:
                        content.append({'text': str(q)})
                    messages.append({'role': 'user', 'content': content})
                    messages.append({'role': 'assistant', 'content': [{'text': str(a)}]})
                    content = []
            
            if messages:
                messages.pop()
            
            for response in call_local_model(model, processor, messages, backend):
                if _chatbot and len(_chatbot) > 0:
                    _chatbot[-1] = (_parse_text(str(chat_query)), _remove_image_special(_parse_text(response)))
                yield _chatbot
            
            full_response = _parse_text(response)
            if task_history and len(task_history) > 0:
                task_history[-1] = (query, full_response)
            print('Qwen-VL-Chat: ' + _parse_text(full_response))
            yield _chatbot
        return predict

    def create_regenerate_fn():
        def regenerate(_chatbot, task_history):
            nonlocal model, processor, backend
            if not task_history:
                return _chatbot
            item = task_history[-1]
            if item[1] is None:
                return _chatbot
            task_history[-1] = (item[0], None)
            if _chatbot and len(_chatbot) > 0:
                _chatbot[-1] = (_chatbot[-1][0], None)
            _chatbot_gen = predict(_chatbot, task_history)
            for _chatbot in _chatbot_gen:
                yield _chatbot
        return regenerate

    predict = create_predict_fn()
    regenerate = create_regenerate_fn()

    def add_text(history, task_history, text):
        if not text or len(str(text).strip()) == 0:
            return history, task_history, ''
        history = history if history is not None else []
        task_history = task_history if task_history is not None else []
        history.append((_parse_text(str(text)), None))
        task_history.append((str(text), None))
        return history, task_history, ''

    def add_file(history, task_history, file):
        history = history if history is not None else []
        task_history = task_history if task_history is not None else []
        if file and hasattr(file, 'name'):
            history.append(((file.name,), None))
            task_history.append(((file.name,), None))
        return history, task_history

    def reset_user_input():
        return gr.update(value='')

    def reset_state(_chatbot, task_history):
        task_history.clear()
        _chatbot.clear()
        _gc()
        return []

    with gr.Blocks() as demo:
        gr.Markdown("""
        <p align="center"><img src="https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3-VL/qwen3vllogo.png" style="height: 80px"/></p>
        """)
        gr.Markdown("""<center><font size=8>Qwen3-VL العربي</font></center>""")
        gr.Markdown("""<center><font size=4>مساعد ذكاء اصطناعي عربي متعدد الوسائط</font></center>""")
        gr.Markdown(f"""<center><font size=3>🚀 يعمل على GPU | النموذج: Qwen2-VL-2B</font></center>""")

        chatbot = gr.Chatbot(label='المساعد العربي', elem_classes='control-height', height=500)
        query = gr.Textbox(lines=2, label='أدخل نصك هنا', placeholder='اكتب سؤالك بالعربية...')
        task_history = gr.State([])

        with gr.Row():
            addfile_btn = gr.UploadButton('📁 رفع ملف', file_types=['image', 'video'])
            submit_btn = gr.Button('🚀 إرسال', variant='primary')
            regen_btn = gr.Button('🤔️ إعادة المحاولة')
            empty_bin = gr.Button('🧹 مسح المحادثة')

        submit_btn.click(
            add_text,
            [chatbot, task_history, query],
            [chatbot, task_history, query]
        ).then(
            predict,
            [chatbot, task_history],
            [chatbot],
            show_progress=True
        ).then(
            reset_user_input,
            [],
            [query]
        )

        empty_bin.click(reset_state, [chatbot, task_history], [chatbot], show_progress=True)
        regen_btn.click(regenerate, [chatbot, task_history], [chatbot], show_progress=True)
        addfile_btn.upload(add_file, [chatbot, task_history, addfile_btn], [chatbot, task_history], show_progress=True)

        gr.Markdown("""
        <font size=2>⚠️ تنبيه: هذا العرض التجريبي يخضع لترخيص Qwen3-VL الأصلي.
        نحن ننصح المستخدمين بعدم إنتاج محتوى ضار.
        </font>
        """)

    demo.queue().launch(
        share=args.share,
        inbrowser=args.inbrowser,
        server_port=args.server_port,
        server_name=args.server_name,
    )


@spaces.GPU(duration=120)
def main():
    args = _get_args()
    model, processor, backend = _load_model_processor(args)
    _launch_demo(args, model, processor, backend)


if __name__ == '__main__':
    main()