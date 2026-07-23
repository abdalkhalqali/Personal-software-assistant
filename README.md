---
title: وكيل البرمجة الذكي
emoji: 🤖
colorFrom: pink
colorTo: purple
sdk: docker
pinned: false
---

# 🤖 وكيل البرمجة الذكي — AI Coding Agent

واجهة احترافية لوكيل برمجة بالذكاء الاصطناعي، مع محادثة ذكية، لوحة جانبية متعددة الأقسام، ودعم اللغة العربية والإنجليزية.

## القدرات
- 💬 **محادثة ذكية** مع دعم Markdown وعرض الأكواد
- 📁 **مستكشف المشروع** — عرض الملفات والمجلدات
- 🧠 **التحكم في الوكيل** — 6 أوضاع: مهندس معماري، مطور، مصحح، مراجع، أمان، معلم
- 📟 **طرفية مدمجة** — تنفيذ أوامر النظام
- 🔗 **إدارة Git** — Commit, Push, Pull, Branch
- 🎨 **4 سمات لونية رومانسية** — ورود، شفق، فجر، ساكورا
- 🌐 ** Arabic / English** — تبديل اللغة من الإعدادات

## وضع التشغيل
1. **HF Inference API** (أولاً) — يستخدم `HF_TOKEN`
2. **CPU محلي** (احتياطي) — يعمل دائماً

## المتغيرات المطلوبة
- `HF_TOKEN` — توكن Hugging Face API
- `MODEL_CHECKPOINT` — (اختياري) اسم النموذج

## البنية
```
api_server.py   ← FastAPI backend (port 7860)
frontend/       ← React + Vite + TypeScript UI
Dockerfile      ← Hugging Face Docker Space
```
