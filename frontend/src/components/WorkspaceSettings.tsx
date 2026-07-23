import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import type { ThemeId } from '../lib/themes'
import { themes } from '../lib/themes'
import {
  Settings,
  Globe,
  Palette,
  Key,
  Rocket,
  Save,
  Type,
} from 'lucide-react'

export function WorkspaceSettings() {
  const {
    language, setLanguage,
    themeId, setThemeId,
    projectName, setProjectName,
    programmingLanguage, setProgrammingLanguage,
    framework, setFramework,
    autoSave, setAutoSave,
    fontSize, setFontSize,
  } = useAppStore()
  const t = getTranslations(language)

  return (
    <div className="py-2 px-3 space-y-4">
      {/* Language settings */}
      <div>
        <div className="flex items-center gap-1.5 mb-2.5">
          <Globe size={13} className="text-[var(--color-cyan)]" />
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            {t.workspace.languageSettings}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLanguage('ar')}
            className={`flex-1 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
              language === 'ar'
                ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)] border border-[var(--color-accent)]/30'
                : 'bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] border border-[var(--color-border-main)] hover:bg-[var(--color-glass-hover)]'
            }`}
          >
            {t.workspace.arabic}
          </button>
          <button
            onClick={() => setLanguage('en')}
            className={`flex-1 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
              language === 'en'
                ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)] border border-[var(--color-accent)]/30'
                : 'bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] border border-[var(--color-border-main)] hover:bg-[var(--color-glass-hover)]'
            }`}
          >
            {t.workspace.english}
          </button>
        </div>
      </div>

      {/* Project Info */}
      <div>
        <div className="flex items-center gap-1.5 mb-2.5">
          <Settings size={13} className="text-[var(--color-accent)]" />
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            Project Settings
          </span>
        </div>
        <div className="space-y-2.5">
          {/* Theme selector */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Palette size={13} className="text-[var(--color-pink)]" />
              <span className="text-xs font-medium text-[var(--color-text-primary)]">
                {language === 'ar' ? 'السمة اللونية' : 'Color Theme'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(themes) as ThemeId[]).map((id) => {
                const th = themes[id]
                return (
                  <button
                    key={id}
                    onClick={() => setThemeId(id)}
                    className={`relative p-2.5 rounded-xl text-xs transition-all duration-200 border overflow-hidden ${
                      themeId === id
                        ? 'ring-2 ring-[var(--color-accent)] border-transparent'
                        : 'border-[var(--color-border-main)] hover:border-[var(--color-border-hover)]'
                    }`}
                    style={{
                      background: `linear-gradient(135deg, ${th.surface3}, ${th.surface2})`,
                    }}
                  >
                    {/* Color preview bar */}
                    <div
                      className="absolute top-0 left-0 right-0 h-1"
                      style={{
                        background: `linear-gradient(90deg, ${th.accent}, ${th.purple})`,
                      }}
                    />
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="text-base">{th.emoji}</span>
                      <span className="font-medium" style={{ color: th.textPrimary }}>
                        {language === 'ar' ? th.name : th.nameEn}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 mt-1.5">
                      <span className="w-3 h-3 rounded-full" style={{ background: th.accent }} />
                      <span className="w-3 h-3 rounded-full" style={{ background: th.purple }} />
                      <span className="w-3 h-3 rounded-full" style={{ background: th.pink }} />
                      <span className="w-3 h-3 rounded-full" style={{ background: th.cyan }} />
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <Field label={t.workspace.projectName}>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] px-3 py-2 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all"
            />
          </Field>
          <Field label={t.workspace.programmingLanguage}>
            <select
              value={programmingLanguage}
              onChange={(e) => setProgrammingLanguage(e.target.value)}
              className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] px-3 py-2 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all"
            >
              <option>Python</option>
              <option>JavaScript</option>
              <option>TypeScript</option>
              <option>Java</option>
              <option>Go</option>
              <option>Rust</option>
              <option>C++</option>
            </select>
          </Field>
          <Field label={t.workspace.framework}>
            <input
              type="text"
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] px-3 py-2 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all"
            />
          </Field>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border-main)]" />

      {/* Other settings */}
      <div className="space-y-3">
        <SettingRow icon={Key} label={t.workspace.apiKeys}>
          <button className="text-[10px] px-2.5 py-1 rounded-lg bg-[var(--color-accent-bg)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-all">
            {language === 'ar' ? 'إضافة' : 'Add'}
          </button>
        </SettingRow>

        <SettingRow icon={Rocket} label={t.workspace.deploySettings}>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            Not configured
          </span>
        </SettingRow>

        <SettingRow icon={Save} label={t.workspace.autoSave}>
          <button
            onClick={() => setAutoSave(!autoSave)}
            className={`relative w-9 h-5 rounded-full transition-all duration-200 ${
              autoSave ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-surface-4)]'
            }`}
          >
            <div
              className={`absolute w-3.5 h-3.5 rounded-full bg-white top-0.5 transition-all duration-200 ${
                autoSave ? 'right-0.5' : 'left-0.5'
              }`}
            />
          </button>
        </SettingRow>

        <SettingRow icon={Type} label={t.workspace.fontSize}>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="12"
              max="18"
              value={fontSize}
              onChange={(e) => setFontSize(parseInt(e.target.value))}
              className="w-16 accent-[var(--color-accent)]"
            />
            <span className="text-xs font-mono text-[var(--color-accent)]">{fontSize}</span>
          </div>
        </SettingRow>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[11px] text-[var(--color-text-muted)] mb-1 block">{label}</label>
      {children}
    </div>
  )
}

function SettingRow({
  icon: Icon,
  label,
  children,
}: {
  icon: any
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon size={13} className="text-[var(--color-text-muted)]" />
        <span className="text-xs text-[var(--color-text-secondary)]">{label}</span>
      </div>
      {children}
    </div>
  )
}
