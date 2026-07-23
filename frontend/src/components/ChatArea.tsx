import { useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { ChatMessage } from './ChatMessage'
import { MessageSquareText, Sparkles } from 'lucide-react'

export function ChatArea() {
  const { messages, isStreaming, language } = useAppStore()
  const t = getTranslations(language)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, messages[messages.length - 1]?.content])

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="py-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {/* Streaming indicator */}
            {isStreaming && (
              <div className="flex gap-3 px-4 py-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--color-cyan)] to-[var(--color-accent)] flex items-center justify-center shrink-0">
                  <Sparkles size={15} className="text-white animate-pulse" />
                </div>
                <div className="flex items-center gap-2 py-2">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <span className="text-xs text-[var(--color-text-muted)] mr-2">
                    {t.chat.thinking}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function EmptyState() {
  const { language, agentMode, setAgentMode } = useAppStore()
  const t = getTranslations(language)

  const suggestions = [
    { text: 'أنشئ تطبيق ويب بسيط بلغة Python', icon: '🐍' },
    { text: 'حلل هذا الكود وابحث عن الأخطاء', icon: '🔍' },
    { text: 'أضف نظام مصادقة لمشروع Flask', icon: '🔐' },
    { text: 'اكتب دالة لقراءة ملف JSON', icon: '📄' },
    { text: 'اشرح لي كيفية عمل REST API', icon: '📡' },
    { text: 'حول هذا الكود من JavaScript إلى TypeScript', icon: '🔄' },
  ]

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-lg">
        {/* Logo */}
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-purple)] flex items-center justify-center animate-float shadow-lg shadow-[var(--color-accent)]/20">
          <MessageSquareText size={36} className="text-white" />
        </div>

        <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
          {t.app.title}
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] mb-8">
          {t.chat.tip}
        </p>

        {/* Agent mode selector */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {(['architect', 'developer', 'debugger', 'reviewer', 'security', 'teacher'] as const).map(
            (mode) => (
              <button
                key={mode}
                onClick={() => setAgentMode(mode)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${
                  agentMode === mode
                    ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)] border border-[var(--color-accent)]/30'
                    : 'bg-[var(--color-glass)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)] hover:bg-[var(--color-glass-hover)]'
                }`}
              >
                {t.agent[mode as keyof typeof t.agent] as string}
              </button>
            ),
          )}
        </div>

        {/* Suggestions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              className="glass text-right p-3 rounded-xl text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all duration-200 border border-[var(--color-glass-border)]"
            >
              <span className="ml-2">{s.icon}</span>
              {s.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
