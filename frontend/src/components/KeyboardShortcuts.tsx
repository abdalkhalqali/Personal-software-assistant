import { useEffect, useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { Keyboard } from 'lucide-react'

interface Shortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  labelKey: string
  action: () => void
}

export function useKeyboardShortcuts() {
  const {
    setActivePanel, setSidebarOpen,
  } = useAppStore()

  const shortcuts: Shortcut[] = [
    {
      key: 'k',
      ctrl: true,
      labelKey: 'openChat',
      action: () => {
        setActivePanel(null)
        setSidebarOpen(false)
      },
    },
    {
      key: 'p',
      ctrl: true,
      labelKey: 'searchFile',
      action: () => {
        setActivePanel('project')
        setSidebarOpen(true)
      },
    },
    {
      key: 'j',
      ctrl: true,
      labelKey: 'openTerminal',
      action: () => {
        setActivePanel('terminal')
        setSidebarOpen(true)
      },
    },
    {
      key: 'g',
      ctrl: true,
      labelKey: 'openGit',
      action: () => {
        setActivePanel('git')
        setSidebarOpen(true)
      },
    },
    {
      key: 'Enter',
      ctrl: true,
      labelKey: 'execute',
      action: () => {},
    },
    {
      key: 'f',
      ctrl: true,
      shift: true,
      labelKey: 'projectSearch',
      action: () => {},
    },
  ]

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      for (const s of shortcuts) {
        if (
          e.key.toLowerCase() === s.key.toLowerCase() &&
          e.ctrlKey === !!s.ctrl &&
          e.shiftKey === !!s.shift &&
          !e.altKey &&
          !e.metaKey
        ) {
          e.preventDefault()
          s.action()
          return
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts])

  return shortcuts
}

export function KeyboardShortcutsModal() {
  const { language } = useAppStore()
  const t = getTranslations(language)
  const [isOpen, setIsOpen] = useState(false)
  const shortcuts = useKeyboardShortcuts()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && e.shiftKey) {
        setIsOpen(!isOpen)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="glass-strong rounded-2xl border border-[var(--color-border-main)] w-full max-w-md mx-4 overflow-hidden animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-[var(--color-border-main)]">
          <Keyboard size={16} className="text-[var(--color-accent)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
            {t.shortcuts.title}
          </h2>
        </div>

        {/* Shortcuts list */}
        <div className="p-5 space-y-3">
          {shortcuts.map((s) => (
            <div key={s.labelKey} className="flex items-center justify-between">
              <span className="text-xs text-[var(--color-text-secondary)]">
                {t.shortcuts[s.labelKey as keyof typeof t.shortcuts]}
              </span>
              <div className="flex items-center gap-1">
                {s.ctrl && <Kbd>Ctrl</Kbd>}
                {s.shift && <Kbd>Shift</Kbd>}
                <Kbd>{s.key === 'Enter' ? 'Enter' : s.key.toUpperCase()}</Kbd>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[var(--color-border-main)]">
          <p className="text-[10px] text-[var(--color-text-muted)] text-center">
            {language === 'ar' ? 'اضغط ? + Shift لفتح هذه النافذة' : 'Press Shift+? to open this window'}
          </p>
        </div>
      </div>
    </div>
  )
}

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-[var(--color-surface-3)] border border-[var(--color-border-main)] text-[var(--color-text-secondary)]">
      {children}
    </kbd>
  )
}
