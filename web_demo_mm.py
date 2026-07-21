# web_demo_mm.py - نسخة ZeroGPU

import spaces
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText


@spaces.GPU
def load_model():
    """تحميل النموذج على GPU"""
    model = AutoModelForImageTextToText.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
    return model, processor


# تحميل النموذج مرة واحدة عند بدء التشغيل
model, processor = load_model()


@spaces.GPU
def respond(message, history):
    """دالة الرد - تعمل على GPU"""
    messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        do_sample=True,
        temperature=0.7
    )
    
    response = processor.decode(outputs[0], skip_special_tokens=True)
    if "assistant" in response:
        response = response.split("assistant")[-1].strip()
    return response


# إنشاء الواجهة
def main():
    gr.ChatInterface(
        fn=respond,
        title="🤖 Qwen3-VL العربي",
        description="مساعد ذكاء اصطناعي عربي متعدد الوسائط (ZeroGPU)",
        examples=["مرحباً، من أنت؟", "ما هي قدراتك؟", "كيف يمكنك مساعدتي؟"]
    ).launch()


if __name__ == "__main__":
    main()