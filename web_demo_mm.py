# web_demo_mm.py - نسخة خفيفة جداً لـ GPU

import spaces
import gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText


@spaces.GPU
def main():
    # تحميل النموذج بأقل استخدام للذاكرة
    model = AutoModelForImageTextToText.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")

    # دالة الرد
    def respond(message, history):
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
            max_new_tokens=128,  # ردود قصيرة وسريعة
            do_sample=True,
            temperature=0.7
        )
        
        response = processor.decode(outputs[0], skip_special_tokens=True)
        # استخراج الرد فقط (إزالة السؤال)
        if "assistant" in response:
            response = response.split("assistant")[-1].strip()
        return response

    # واجهة المحادثة
    gr.ChatInterface(
        respond,
        title="🤖 Qwen3-VL العربي",
        description="مساعد ذكاء اصطناعي عربي متعدد الوسائط (نموذج Qwen2-VL-2B)",
        theme="soft"
    ).launch()

if __name__ == "__main__":
    main()