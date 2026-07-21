---
title: Qwen3-VL-Demo
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.20.0
app_file: web_demo_mm.py
pinned: false
---

# Qwen3-VL Multimodal Demo

This Space hosts the Qwen3-VL-2B-Instruct model using Gradio 6.20.0. 

## Local Setup
```bash
pip install -r requirements_web_demo.txt
python web_demo_mm.py --checkpoint-path Qwen/Qwen3-VL-2B-Instruct --backend hf
```
