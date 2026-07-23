import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import {
  RefreshCw,
  Trash2,
  RotateCcw,
  Info,
  Cpu,
  GitCompare,
  CheckCircle2,
} from 'lucide-react'

export function MemoryPanel() {
  const { language, deleteMemory, reanalyzeProject } = useAppStore()
  const t = getTranslations(language)

  const items = [
    {
      icon: Info,
      label: t.memory.projectInfo,
      value: 'مساعد البرمجة الشخصي — Qwen3-VL',
      color: 'text-[var(--color-accent)]',
    },
    {
      icon: Cpu,
      label: t.memory.technologies,
      value: 'Python, Gradio, Qwen3-VL, Transformers, Hugging Face',
      color: 'text-[var(--color-cyan)]',
    },
    {
      icon: GitCompare,
      label: t.memory.decisions,
      value: 'استخدام HF Inference API كأساسي و CPU كاحتياطي',
      color: 'text-[var(--color-warning)]',
    },
    {
      icon: CheckCircle2,
      label: t.memory.resolvedIssues,
      value: 'تحميل النموذج المحلي فقط عند فشل API (Lazy Loading)',
      color: 'text-[var(--color-success)]',
    },
  ]

  return (
    <div className="py-2 px-3 space-y-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="p-3 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border-main)]"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <item.icon size={14} className={item.color} />
            <span className="text-xs font-medium text-[var(--color-text-primary)]">
              {item.label}
            </span>
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
            {item.value}
          </p>
        </div>
      ))}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => {}}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-[var(--color-accent-bg)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-all"
        >
          <RefreshCw size={13} />
          {t.memory.update}
        </button>
        <button
          onClick={deleteMemory}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-[var(--color-danger-bg)] text-[var(--color-danger)] hover:bg-[var(--color-danger)]/20 transition-all"
        >
          <Trash2 size={13} />
        </button>
        <button
          onClick={reanalyzeProject}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] hover:bg-[var(--color-glass-hover)] transition-all"
        >
          <RotateCcw size={13} />
        </button>
      </div>
    </div>
  )
}
