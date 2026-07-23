
import gradio as gr
import time

# CSS قسري لضمان ظهور النص باللون الأبيض مهما كانت الظروف
css = """

body { direction: rtl; }
.gradio-container { background-color: #0b0f19 !important; }
#chatbot .message-wrap.user .message-body { background-color: #1a73e8 !important; color: white !important; border-radius: 15px; padding: 10px 15px; margin-left: 10px; text-align: right; }
#chatbot .message-wrap.bot .message-body { background-color: #333 !important; color: white !important; border-radius: 15px; padding: 10px 15px; margin-right: 10px; text-align: right; }
#chatbot .message-text { color: white !important; }
#chatbot span { color: white !important; }
#chatbot p { color: white !important; }
input { color: white !important; }

"""

def respond(message, history):
    bot_message = f"وعليكم السلام ورحمة الله وبركاته! أنا هنا لمساعدتك. لقد استلمت رسالتك: '{{message}}'. كيف يمكنني دعم مشروعك البرمجي اليوم؟"
    print(f"DEBUG: Generated bot_message: {{bot_message}}") # Debug statement
    history.append({{"role": "user", "content": message}})
    history.append({{"role": "assistant", "content": ""}})
    for i in range(len(bot_message)):
        time.sleep(0.01)
        history[-1]['content'] = bot_message[:i+1]
        yield "", history

with gr.Blocks(title="AI Nexus Assistant v5.6") as demo:
    gr.Markdown("<h1 style='text-align:center; color:white;'>🚀 AI Nexus Assistant v5.6</h1>")

    # Removed 'type="messages"' as it causes TypeError
    chatbot = gr.Chatbot(elem_id="chatbot", height=550, render_markdown=True)
    with gr.Row():
        msg = gr.Textbox(placeholder="اكتب هنا...", scale=9, container=False)
        submit = gr.Button("إرسال", scale=1, variant="primary")

    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    submit.click(respond, [msg, chatbot], [msg, chatbot])

if __name__ == '__main__':
    demo.launch(share=True, css=css)
