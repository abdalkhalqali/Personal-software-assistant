# web_demo_mm.py - نسخة سريعة مع Flash Attention

import spaces
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText


@spaces.GPU
def load_model():
    model = AutoModelForImageTextToText.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        torch_dtype=torch.float16,
        attn_implementation="flash_attention_2",  # ⚡ تسريع
        device_map="auto",
        low_cpu_mem_usage=True
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
    return model, processor


model, processor = load_model()


@spaces.GPU
def respond(message, history):
    messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # ⚡ إعدادات سريعة
    outputs = model.generate(
        **inputs,
        max_new_tokens=64,
        do_sample=False,
        temperature=0.1,
        num_beams=1,
        use_cache=True
    )
    
    response = processor.decode(outputs[0], skip_special_tokens=True)
    if "assistant" in response:
        response = response.split("assistant")[-1].strip()
    return response


def main():
    gr.ChatInterface(
        fn=respond,
        title="🤖 Qwen3-VL العربي (سريع)",
        description="مساعد ذكاء اصطناعي عربي - مع Flash Attention",
        examples=["مرحباً", "من أنت؟", "كيف الحال؟"]
    ).launch()


if __name__ == "__main__":
    main()