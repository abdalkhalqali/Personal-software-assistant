import { useState, useRef, type KeyboardEvent, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { executeCommand } from '../lib/api'
import {
  Play,
  Trash2,
  Terminal,
} from 'lucide-react'

export function TerminalPanel() {
  const { language, terminalHistory, addTerminalLine, clearTerminal } = useAppStore()
  const t = getTranslations(language)
  const [command, setCommand] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [terminalHistory])

  const handleRun = async () => {
    const cmd = command.trim()
    if (!cmd || isRunning) return

    setCommand('')
    setIsRunning(true)
    addTerminalLine(`$ ${cmd}`)

    const output = await executeCommand(cmd)
    if (output) {
      addTerminalLine(output)
    }
    setIsRunning(false)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleRun()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Terminal output */}
      <div
        ref={outputRef}
        className="flex-1 overflow-y-auto p-3 bg-[var(--color-terminal-bg)] font-mono text-xs leading-relaxed space-y-1 mx-3 rounded-xl"
        style={{ minHeight: '120px' }}
      >
        {terminalHistory.map((line, i) => (
          <div
            key={i}
            className={`${
              line.startsWith('$')
                ? 'text-[var(--color-success)]'
                : line.startsWith('Error') || line.startsWith('❌')
                ? 'text-[var(--color-danger)]'
                : 'text-[var(--color-text-secondary)]'
            }`}
          >
            {line}
          </div>
        ))}
        <div className="flex items-center gap-1 text-[var(--color-success)]">
          <span>$</span>
          <span className="terminal-cursor" />
        </div>
      </div>

      {/* Command input */}
      <div className="px-3 pt-2 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t.terminal.placeholder}
              className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] px-3 py-2 pr-8 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all font-mono"
            />
            <Terminal size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          </div>
          <button
            onClick={handleRun}
            disabled={!command.trim() || isRunning}
            className="p-2 rounded-lg bg-[var(--color-accent-bg)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 disabled:opacity-50 transition-all"
          >
            <Play size={14} />
          </button>
          <button
            onClick={clearTerminal}
            className="p-2 rounded-lg hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] transition-all"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
