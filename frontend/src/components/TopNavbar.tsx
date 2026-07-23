import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import {
  MessageSquareText,
  Code2,
  FolderTree,
  Terminal,
  GitBranch,
  FlaskConical,
  Rocket,
  PanelLeft,
  Menu,
} from 'lucide-react'

export function TopNavbar() {
  const { language, sidebarOpen, toggleSidebar, setActivePanel } = useAppStore()
  const t = getTranslations(language)

  const buttons = [
    { icon: MessageSquareText, label: t.nav.chat, action: () => setActivePanel(null) },
    { icon: Code2, label: t.nav.code, action: () => {} },
    { icon: FolderTree, label: t.nav.files, action: () => setActivePanel('project') },
    { icon: Terminal, label: t.nav.terminal, action: () => setActivePanel('terminal') },
    { icon: GitBranch, label: t.nav.git, action: () => setActivePanel('git') },
    { icon: FlaskConical, label: t.nav.test, action: () => {} },
    { icon: Rocket, label: t.nav.deploy, action: () => {} },
  ]

  return (
    <header className="glass-strong h-14 px-4 flex items-center justify-between shrink-0 z-50">
      {/* Left section */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-[var(--color-glass-hover)] transition-colors duration-150"
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? (
            <PanelLeft size={20} className="text-[var(--color-text-secondary)]" />
          ) : (
            <Menu size={20} className="text-[var(--color-text-secondary)]" />
          )}
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-purple)] flex items-center justify-center animate-glow">
            <Code2 size={16} className="text-white" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-sm font-semibold text-[var(--color-text-primary)] leading-tight">
              {t.app.title}
            </h1>
            <p className="text-[10px] text-[var(--color-text-muted)] leading-tight">
              {t.app.version}
            </p>
          </div>
        </div>
      </div>

      {/* Center - Quick actions */}
      <div className="hidden md:flex items-center gap-1">
        {buttons.map((btn) => (
          <button
            key={btn.label}
            onClick={btn.action}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all duration-150"
          >
            <btn.icon size={15} />
            <span>{btn.label}</span>
          </button>
        ))}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--color-success)]/10 border border-[var(--color-success)]/20">
          <span className="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" />
          <span className="text-[11px] text-[var(--color-success)] font-medium">
            {t.app.status}
          </span>
        </div>
      </div>
    </header>
  )
}
