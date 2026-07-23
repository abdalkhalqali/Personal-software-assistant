import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { cn } from '../lib/utils'
import {
  FolderTree,
  Bot,
  Bookmark,
  Terminal,
  GitBranch,
  Gauge,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { ProjectExplorer } from './ProjectExplorer'
import { AIAgentControl } from './AIAgentControl'
import { MemoryPanel } from './MemoryPanel'
import { TerminalPanel } from './TerminalPanel'
import { GitManager } from './GitManager'
import { ModelSettings } from './ModelSettings'
import { WorkspaceSettings } from './WorkspaceSettings'

const panels = [
  { id: 'project', icon: FolderTree, labelKey: 'projectExplorer', component: ProjectExplorer },
  { id: 'agent', icon: Bot, labelKey: 'aiControl', component: AIAgentControl },
  { id: 'memory', icon: Bookmark, labelKey: 'memory', component: MemoryPanel },
  { id: 'terminal', icon: Terminal, labelKey: 'terminal', component: TerminalPanel },
  { id: 'git', icon: GitBranch, labelKey: 'gitManager', component: GitManager },
  { id: 'model', icon: Gauge, labelKey: 'modelSettings', component: ModelSettings },
  { id: 'workspace', icon: Settings, labelKey: 'workspaceSettings', component: WorkspaceSettings },
] as const

type PanelId = typeof panels[number]['id']

export function Sidebar() {
  const { language, sidebarOpen, activePanel, setActivePanel, toggleSidebar } = useAppStore()
  const t = getTranslations(language)

  return (
    <>
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={toggleSidebar}
        />
      )}

      <aside
        className={cn(
          'h-full flex transition-all duration-300 ease-in-out relative z-40',
          sidebarOpen ? 'w-[320px]' : 'w-0 md:w-0 overflow-hidden',
        )}
      >
        <div className="w-[320px] h-full glass-strong border-l border-[var(--color-border-main)] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-main)] shrink-0">
            <h2 className="text-xs font-semibold text-[var(--color-text-primary)]">
              {activePanel
                ? t.sidebar[`${activePanel}Settings` as keyof typeof t.sidebar] ||
                  t.sidebar[activePanel as keyof typeof t.sidebar]
                : '☰'} 
            </h2>
            <button
              onClick={toggleSidebar}
              className="p-1 rounded-lg hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
            >
              {language === 'ar' ? (
                <ChevronRight size={16} />
              ) : (
                <ChevronLeft size={16} />
              )}
            </button>
          </div>

          {/* Panel navigation tabs */}
          <div className="flex items-center gap-0.5 px-2 py-2 border-b border-[var(--color-border-main)] overflow-x-auto shrink-0">
            {panels.map(({ id, icon: Icon, labelKey }) => (
              <button
                key={id}
                onClick={() => setActivePanel(id as PanelId)}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all duration-150 whitespace-nowrap',
                  activePanel === id
                    ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]'
                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)]',
                )}
                title={t.sidebar[labelKey as keyof typeof t.sidebar] as string}
              >
                <Icon size={13} />
                <span className="hidden sm:inline">
                  {t.sidebar[labelKey as keyof typeof t.sidebar] as string}
                </span>
              </button>
            ))}
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto">
            {panels.map(({ id, component: Component }) => (
              <div
                key={id}
                className={cn(
                  activePanel === id ? 'block' : 'hidden',
                )}
              >
                <Component />
              </div>
            ))}
          </div>
        </div>
      </aside>
    </>
  )
}
