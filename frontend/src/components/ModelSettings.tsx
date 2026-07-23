import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import {
  Cpu,
  CircuitBoard,
  HardDrive,
  Clock,
  Gauge,
} from 'lucide-react'

export function ModelSettings() {
  const {
    language, temperature, setTemperature,
    maxTokens, setMaxTokens, systemStats,
  } = useAppStore()
  const t = getTranslations(language)

  return (
    <div className="py-2 px-3 space-y-4">
      {/* Model selector */}
      <div>
        <label className="text-xs font-medium text-[var(--color-text-secondary)] mb-1.5 block">
          {t.model.model}
        </label>
        <select className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] px-3 py-2 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all appearance-none cursor-pointer">
          <option>Qwen3-VL-2B-Instruct</option>
          <option>Qwen3-VL-7B-Instruct</option>
          <option>Qwen3-VL-30B-Instruct</option>
        </select>
      </div>

      {/* Temperature */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-[var(--color-text-secondary)]">
            {t.model.temperature}
          </label>
          <span className="text-xs font-mono text-[var(--color-accent)]">
            {temperature.toFixed(1)}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          value={temperature}
          onChange={(e) => setTemperature(parseFloat(e.target.value))}
          className="w-full accent-[var(--color-accent)]"
        />
        <div className="flex justify-between text-[9px] text-[var(--color-text-muted)] mt-0.5">
          <span>دقيق</span>
          <span>إبداعي</span>
        </div>
      </div>

      {/* Max tokens */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-[var(--color-text-secondary)]">
            {t.model.maxTokens}
          </label>
          <span className="text-xs font-mono text-[var(--color-accent)]">
            {maxTokens.toLocaleString()}
          </span>
        </div>
        <input
          type="range"
          min="512"
          max="8192"
          step="512"
          value={maxTokens}
          onChange={(e) => setMaxTokens(parseInt(e.target.value))}
          className="w-full accent-[var(--color-accent)]"
        />
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border-main)]" />

      {/* System stats */}
      <div>
        <div className="flex items-center gap-1.5 mb-2.5">
          <Gauge size={13} className="text-[var(--color-cyan)]" />
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            System Stats
          </span>
        </div>

        <div className="space-y-2.5">
          <StatBar
            icon={Cpu}
            label={t.model.cpuUsage}
            value={`${systemStats.cpu}%`}
            progress={systemStats.cpu}
            color="var(--color-accent)"
          />
          <StatBar
            icon={CircuitBoard}
            label={t.model.gpuUsage}
            value={`${systemStats.gpu}%`}
            progress={systemStats.gpu}
            color="var(--color-purple)"
          />
          <StatBar
            icon={HardDrive}
            label={t.model.ram}
            value={`${systemStats.ram}%`}
            progress={systemStats.ram}
            color="var(--color-cyan)"
          />
          <StatBar
            icon={Clock}
            label={t.model.responseTime}
            value={`${systemStats.responseTime}ms`}
            progress={Math.min(systemStats.responseTime / 20, 100)}
            color="var(--color-warning)"
          />
        </div>
      </div>
    </div>
  )
}

function StatBar({
  icon: Icon,
  label,
  value,
  progress,
  color,
}: {
  icon: any
  label: string
  value: string
  progress: number
  color: string
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <Icon size={11} className="text-[var(--color-text-muted)]" />
          <span className="text-[11px] text-[var(--color-text-secondary)]">{label}</span>
        </div>
        <span className="text-[11px] font-mono text-[var(--color-text-primary)]">{value}</span>
      </div>
      <div className="h-1 rounded-full bg-[var(--color-surface-4)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${Math.min(progress, 100)}%`,
            background: `linear-gradient(90deg, ${color}, ${color}88)`,
          }}
        />
      </div>
    </div>
  )
}
