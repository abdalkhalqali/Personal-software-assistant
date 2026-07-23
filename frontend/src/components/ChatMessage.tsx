import type { Message, CodeBlock } from '../stores/appStore'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { cn } from '../lib/utils'
import {
  FileCode,
  User,
  Bot,
} from 'lucide-react'

interface Props {
  message: Message
  codeBlocks?: CodeBlock[]
}

export function ChatMessage({ message, codeBlocks = [] }: Props) {
  const { language, isStreaming } = useAppStore()
  const t = getTranslations(language)
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={cn(
        'flex gap-3 px-4 py-5 message-enter',
        isUser ? 'flex-row-reverse' : 'flex-row',
      )}
      style={{ animationDelay: '0.05s' }}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5',
          isUser
            ? 'bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-purple)]'
            : 'bg-gradient-to-br from-[var(--color-cyan)] to-[var(--color-accent)]',
        )}
      >
        {isUser ? (
          <User size={15} className="text-white" />
        ) : (
          <Bot size={15} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn('flex-1 min-w-0', isUser ? 'max-w-[80%]' : 'max-w-full')}>
        {/* Role label */}
        <div className="text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
          {isUser ? '' : '🧠 ' + t.app.title}
        </div>

        {/* Message text - render as plain text with inline styles for reliability */}
        {message.content && (
          <div style={{ color: '#e6edf3', fontSize: '14px', lineHeight: '1.7', whiteSpace: 'pre-wrap', wordBreak: 'break-word', backgroundColor: 'rgba(255,255,255,0.05)', padding: '8px 12px', borderRadius: '8px' }}>
            {message.content}
          </div>
        )}

        {/* Streaming indicator */}
        {isAssistant && isStreaming && !message.content && (
          <div className="flex items-center gap-2 py-2">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
            <span className="text-xs text-[var(--color-text-muted)] mr-2">
              {t.chat.thinking}
            </span>
          </div>
        )}

        {/* Code blocks from structured data */}
        {codeBlocks.map((block) => (
          <CodeBlockCard key={block.id} block={block} />
        ))}
      </div>
    </div>
  )
}

function CodeBlockCard({ block }: { block: CodeBlock }) {
  const { language: lang } = useAppStore()
  const t = getTranslations(lang)

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-[var(--color-border-main)] bg-[var(--color-code-bg)]">
      <div className="flex items-center justify-between px-3 py-2 bg-[var(--color-surface-3)] border-b border-[var(--color-border-main)]">
        <div className="flex items-center gap-2">
          <FileCode size={14} className="text-[var(--color-text-muted)]" />
          <span className="text-xs font-mono text-[var(--color-text-muted)]">
            {block.language}
            {block.filename && (
              <span className="mr-1.5 text-[var(--color-accent)]">{block.filename}</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button className="p-1.5 rounded-md hover:bg-[var(--color-accent-bg)] text-[var(--color-accent)] text-xs font-medium transition-all">
            {t.chat.applyEdit}
          </button>
          <button className="p-1.5 rounded-md hover:bg-[var(--color-danger-bg)] text-[var(--color-danger)] text-xs font-medium transition-all">
            {t.chat.rejectEdit}
          </button>
        </div>
      </div>
      <pre className="p-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-[var(--color-text-primary)]">
        <code>{block.code}</code>
      </pre>
    </div>
  )
}
