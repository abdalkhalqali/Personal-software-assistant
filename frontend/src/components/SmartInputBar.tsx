import { useState, useRef, type KeyboardEvent } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { sendMessage } from '../lib/api'
import {
  Paperclip,
  FolderUp,
  FolderOpen,
  Square,
  ArrowUp,
} from 'lucide-react'
import { cn } from '../lib/utils'

export function SmartInputBar() {
  const { language, addMessage, setStreaming, updateMessage, messages, agentMode } = useAppStore()
  const t = getTranslations(language)
  const [input, setInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isProcessing) return

    setInput('')
    setIsProcessing(true)
    setStreaming(true)

    // Add user message
    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user' as const,
      content: text,
      timestamp: Date.now(),
    }
    addMessage(userMsg)

    // Create assistant message placeholder
    const assistantId = `msg-${Date.now() + 1}`
    const assistantMsg = {
      id: assistantId,
      role: 'assistant' as const,
      content: '',
      timestamp: Date.now() + 1,
      isStreaming: true,
    }
    addMessage(assistantMsg)

    let fullText = ''

    await sendMessage(
      [...messages, userMsg],
      (token) => {
        fullText += token
        updateMessage(assistantId, { content: fullText })
      },
      (text) => {
        updateMessage(assistantId, { content: text, isStreaming: false })
        setIsProcessing(false)
        setStreaming(false)
      },
      (error) => {
        updateMessage(assistantId, {
          content: `❌ **خطأ:** ${error}\n\n${t.chat.retry}`,
          isStreaming: false,
        })
        setIsProcessing(false)
        setStreaming(false)
      },
    )
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="shrink-0 px-4 pb-4 pt-2">
      <div className="max-w-4xl mx-auto">
        {/* Agent mode badge */}
        <div className="flex items-center gap-2 mb-2 px-1">
          <span className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            {language === 'ar' ? 'الوضع:' : 'Mode:'}
          </span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[var(--color-accent-bg)] text-[var(--color-accent)] border border-[var(--color-accent)]/20">
            {t.agent[agentMode]}
          </span>
        </div>

        {/* Input area */}
        <div className="relative glass rounded-2xl border border-[var(--color-glass-border)] focus-within:border-[var(--color-accent)]/50 transition-all duration-200 shadow-lg shadow-black/20">
          {/* Action buttons row */}
          <div className="flex items-center gap-1 px-3 pt-2.5 pb-1 border-b border-[var(--color-border-main)]/50">
            <button
              className="p-1.5 rounded-lg hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
              title={t.chat.attachFile}
            >
              <Paperclip size={15} />
            </button>
            <button
              className="p-1.5 rounded-lg hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
              title={t.chat.uploadZip}
            >
              <FolderUp size={15} />
            </button>
            <button
              className="p-1.5 rounded-lg hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
              title={t.chat.pickFile}
            >
              <FolderOpen size={15} />
            </button>
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t.chat.placeholder}
            rows={2}
            className="w-full bg-transparent px-4 py-3 text-sm text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] resize-none outline-none font-sans"
            style={{ minHeight: '48px', maxHeight: '160px' }}
          />

          {/* Bottom row */}
          <div className="flex items-center justify-between px-3 pb-2.5">
            <div className="flex items-center gap-1">
              {isProcessing && (
                <button
                  onClick={() => {
                    setIsProcessing(false)
                    setStreaming(false)
                  }}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--color-danger)]/10 text-[var(--color-danger)] text-xs font-medium hover:bg-[var(--color-danger)]/20 transition-all"
                >
                  <Square size={12} />
                  {t.chat.stop}
                </button>
              )}
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isProcessing}
              className={cn(
                'p-2 rounded-xl transition-all duration-200',
                input.trim() && !isProcessing
                  ? 'bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-purple)] text-white hover:shadow-lg hover:shadow-[var(--color-accent)]/25'
                  : 'bg-[var(--color-surface-4)] text-[var(--color-text-muted)] cursor-not-allowed',
              )}
            >
              {isProcessing ? (
                <Square size={16} />
              ) : (
                <ArrowUp size={16} />
              )}
            </button>
          </div>
        </div>

        {/* Tip */}
        <p className="text-[10px] text-[var(--color-text-muted)] text-center mt-2 opacity-60">
          {t.chat.tip}
          {language === 'ar' ? ' · Ctrl+Enter للإرسال' : ' · Ctrl+Enter to send'}
        </p>
      </div>
    </div>
  )
}
