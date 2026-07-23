
import gradio as gr
import os

custom_css = \"\"\"
body { direction: rtl; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.gradio-container { background: #0d1117; color: #c9d1d9; }
.navbar {
    background: rgba(22, 27, 34, 0.8);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid #30363d;
    padding: 10px 20px;
    position: sticky; top: 0; z-index: 1000;
}
.sidebar {
    background: #161b22;
    border-left: 1px solid #30363d;
    width: 300px;
    transition: 0.3s;
    overflow-y: auto;
    padding: 15px;
}
.chat-area { flex-grow: 1; display: flex; flex-direction: column; padding: 20px; }
.terminal-box { background: #000; color: #00ff00; font-family: 'Courier New', monospace; padding: 10px; border-radius: 5px; }
\"\"\"

with gr.Blocks(css=custom_css, title=\"AI Coding Agent - Professional IDE\") as demo:
    with gr.Row(elem_classes=\"navbar\"):
        with gr.Column(scale=1):
            gr.Markdown(\"### 🤖 وكيل البرمجة الذكي\")
        with gr.Column(scale=3):
            with gr.Row():
                gr.Button(\"💬 المحادثة\", size=\"sm\")
                gr.Button(\"📄 الكود\", size=\"sm\")
                gr.Button(\"📁 الملفات\", size=\"sm\")
                gr.Button(\"📟 الطرفية\", size=\"sm\")
        with gr.Column(scale=1):
             gr.Markdown(\"🟢 متصل | v3.0\")

    with gr.Row():
        with gr.Column(scale=4, elem_classes=\"chat-area\"):
            chatbot = gr.Chatbot(label=\"مهندس البرمجيات الذكي\", height=600, show_label=False)
            with gr.Row():
                msg = gr.Textbox(placeholder=\"اكتب طلبك هنا...\", scale=9, show_label=False)
                submit_btn = gr.Button(\"إرسال\", scale=1, variant=\"primary\")

        with gr.Column(scale=1, elem_classes=\"sidebar\"):
            with gr.Accordion(\"📂 مستكشف المشروع\", open=True):
                gr.FileExplorer(root_dir=\".\", label=\"الملفات\")
            with gr.Accordion(\"🧠 التحكم\", open=False):
                gr.Radio([\"Architect\", \"Developer\"], label=\"الوضع\")
            with gr.Accordion(\"📟 الطرفية\", open=False):
                gr.Code(\"$ echo 'System Ready'\", language=\"shell\", elem_classes=\"terminal-box\")

if __name__ == '__main__':
    demo.launch(share=True)
