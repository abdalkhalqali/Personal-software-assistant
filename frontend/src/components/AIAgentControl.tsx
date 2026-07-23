import { useAppStore, type AgentMode } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { cn } from '../lib/utils'
import {
  Building2,
  Code2,
  Bug,
  Search,
  Shield,
  GraduationCap,
  Check,
} from 'lucide-react'

const agentConfig: { mode: AgentMode; icon: any; color: string }[] = [
  { mode: 'architect', icon: Building2, color: 'from-purple-500 to-blue-500' },
  { mode: 'developer', icon: Code2, color: 'from-blue-500 to-cyan-500' },
  { mode: 'debugger', icon: Bug, color: 'from-orange-500 to-red-500' },
  { mode: 'reviewer', icon: Search, color: 'from-green-500 to-emerald-500' },
  { mode: 'security', icon: Shield, color: 'from-red-500 to-pink-500' },
  { mode: 'teacher', icon: GraduationCap, color: 'from-yellow-500 to-orange-500' },
]

export function AIAgentControl() {
  const { language, agentMode, setAgentMode } = useAppStore()
  const t = getTranslations(language)

  return (
    <div className="py-2 px-3 space-y-2">
      {agentConfig.map(({ mode, icon: Icon, color }) => (
        <button
          key={mode}
          onClick={() => setAgentMode(mode)}
          className={cn(
            'w-full flex items-center gap-3 p-2.5 rounded-xl transition-all duration-200 text-right',
            agentMode === mode
              ? 'bg-[var(--color-accent-bg)] border border-[var(--color-accent)]/20'
              : 'hover:bg-[var(--color-glass-hover)] border border-transparent',
          )}
        >
          {/* Icon */}
          <div className={cn(
            'w-9 h-9 rounded-xl bg-gradient-to-br flex items-center justify-center shrink-0',
            color,
          )}>
            <Icon size={16} className="text-white" />
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-sm font-medium',
                agentMode === mode ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-primary)]',
              )}>
                {t.agent[mode]}
              </span>
              {agentMode === mode && (
                <Check size={12} className="text-[var(--color-accent)]" />
              )}
            </div>
            <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
              {t.agent[`${mode}Desc` as keyof typeof t.agent] as string}
            </p>
          </div>
        </button>
      ))}
    </div>
  )
}
