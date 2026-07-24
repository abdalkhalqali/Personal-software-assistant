import { useState, useEffect, useCallback } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { fetchApiKeys, addApiKey, deleteApiKey, testApiKey } from '../lib/api'
import {
  Key,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  Eye,
  EyeOff,
  AlertCircle,
  Shield,
  Gauge,
  Cpu,
  HardDrive,
  CircuitBoard,
  Clock,
  Search,
  BarChart3,
  Zap,
  ExternalLink,
} from 'lucide-react'

const PROVIDER_META: Record<string, { icon: string; color: string; docUrl: string }> = {
  groq: { icon: '⚡', color: '#f97316', docUrl: 'https://console.groq.com' },
  openai: { icon: '🔵', color: '#10a37f', docUrl: 'https://platform.openai.com/api-keys' },
  gemini: { icon: '🟢', color: '#4285f4', docUrl: 'https://aistudio.google.com/apikey' },
  hf: { icon: '🤗', color: '#ffd21e', docUrl: 'https://huggingface.co/settings/tokens' },
}

export function ModelSettings() {
  const {
    language, temperature, setTemperature,
    maxTokens, setMaxTokens, systemStats,
    apiKeys, setApiKeys,
  } = useAppStore()
  const t = getTranslations(language)
  const isAr = language === 'ar'

  // Load keys on mount
  useEffect(() => {
    loadKeys()
  }, [])

  const loadKeys = async () => {
    try {
      const data = await fetchApiKeys()
      const transformed: Record<string, any[]> = {}
      for (const [provider, info] of Object.entries(data)) {
        transformed[provider] = (info as any).keys || []
      }
      setApiKeys(transformed)
    } catch {
      // Ignore
    }
  }

  return (
    <div className="py-2 px-3 space-y-4 overflow-y-auto max-h-[calc(100vh-200px)]">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <Key size={14} className="text-[var(--color-accent)]" />
        <span className="text-xs font-bold text-[var(--color-text-primary)] tracking-wide uppercase">
          {isAr ? 'مفاتيح API' : 'API Keys'}
        </span>
      </div>
      <p className="text-[10px] text-[var(--color-text-muted)] leading-relaxed">
        {isAr
          ? 'أضف مفاتيح API من مزودين متعددين. يدعم النظام حتى 100+ مفتاح لكل مزود مع التبديل التلقائي عند فشل أي مفتاح.'
          : 'Add API keys from multiple providers. Supports up to 100+ keys per provider with automatic failover.'}
      </p>

      {/* Provider Sections */}
      <div className="space-y-3">
        {Object.entries(PROVIDER_META).map(([provider, meta]) => (
          <ProviderSection
            key={provider}
            provider={provider}
            icon={meta.icon}
            docUrl={meta.docUrl}
            keys={apiKeys[provider] || []}
            onKeysChanged={loadKeys}
          />
        ))}
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border-main)]" />

      {/* Model Parameters */}
      <div>
        <div className="flex items-center gap-1.5 mb-2.5">
          <Gauge size={13} className="text-[var(--color-cyan)]" />
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            {isAr ? 'إعدادات النموذج' : 'Model Settings'}
          </span>
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
            <span>{isAr ? 'دقيق' : 'Precise'}</span>
            <span>{isAr ? 'إبداعي' : 'Creative'}</span>
          </div>
        </div>

        {/* Max tokens */}
        <div className="mt-3">
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
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border-main)]" />

      {/* System stats */}
      <div>
        <div className="flex items-center gap-1.5 mb-2.5">
          <Shield size={13} className="text-[var(--color-accent)]" />
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            {isAr ? 'إحصائيات النظام' : 'System Stats'}
          </span>
        </div>
        <div className="space-y-2.5">
          <StatBar icon={Cpu} label={t.model.cpuUsage} value={`${systemStats.cpu}%`} progress={systemStats.cpu} color="var(--color-accent)" />
          <StatBar icon={CircuitBoard} label={t.model.gpuUsage} value={`${systemStats.gpu}%`} progress={systemStats.gpu} color="var(--color-purple)" />
          <StatBar icon={HardDrive} label={t.model.ram} value={`${systemStats.ram}%`} progress={systemStats.ram} color="var(--color-cyan)" />
          <StatBar icon={Clock} label={t.model.responseTime} value={`${systemStats.responseTime}ms`} progress={Math.min(systemStats.responseTime / 20, 100)} color="var(--color-warning)" />
        </div>
      </div>
    </div>
  )
}

// ── Provider Section ──────────────────────────────────────────────────────
function ProviderSection({
  provider,
  icon,
  docUrl,
  keys,
  onKeysChanged,
}: {
  provider: string
  icon: string
  docUrl: string
  keys: any[]
  onKeysChanged: () => void
}) {
  const { language, addApiKey: addKeyToStore, removeApiKey: removeKeyFromStore } = useAppStore()
  const isAr = language === 'ar'
  const [isAdding, setIsAdding] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any>(null)
  const [showInspectModal, setShowInspectModal] = useState<any>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const providerName = provider === 'groq' ? 'Groq' : provider === 'openai' ? 'OpenAI' : provider === 'gemini' ? 'Gemini' : 'HuggingFace'
  const envKey = keys.find(k => k.id === 'env')

  const handleAdd = useCallback(async () => {
    const key = newKey.trim()
    if (!key) return
    setIsSubmitting(true)
    try {
      const result = await addApiKey(provider, key, newLabel.trim())
      if (result.status === 'ok') {
        addKeyToStore(provider, result.key)
        setNewKey('')
        setNewLabel('')
        setIsAdding(false)
        onKeysChanged()
      } else {
        alert(result.message || (isAr ? 'فشل إضافة المفتاح' : 'Failed to add key'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }, [provider, newKey, newLabel, isAr, addKeyToStore, onKeysChanged])

  const handleDelete = useCallback(async (keyId: string) => {
    if (!confirm(isAr ? 'هل أنت متأكد من حذف هذا المفتاح؟' : 'Are you sure you want to delete this key?')) return
    const result = await deleteApiKey(provider, keyId)
    if (result.status === 'ok') {
      removeKeyFromStore(provider, keyId)
      onKeysChanged()
    }
  }, [provider, isAr, removeKeyFromStore, onKeysChanged])

  const handleTest = useCallback(async (keyId: string, key: string) => {
    setTestingId(keyId)
    setTestResult(null)
    try {
      const result = await testApiKey(provider, key)
      setTestResult({ id: keyId, ...result })
      setShowInspectModal({ id: keyId, ...result })
    } finally {
      setTestingId(null)
    }
  }, [provider])

  const nonEnvKeys = keys.filter(k => k.id !== 'env')

  return (
    <>
      <div className="rounded-xl border border-[var(--color-border-main)] overflow-hidden bg-[var(--color-surface-2)]/50">
        {/* Provider header */}
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--color-border-main)]">
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <div>
              <span className="text-xs font-semibold text-[var(--color-text-primary)]">{providerName}</span>
              <span className="text-[9px] text-[var(--color-text-muted)] mr-2">
                {keys.length} {isAr ? 'مفتاح' : 'key'}{keys.length !== 1 ? (isAr ? '' : 's') : ''}
              </span>
            </div>
          </div>
          <a
            href={docUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[9px] text-[var(--color-accent)] hover:underline opacity-70 hover:opacity-100 transition-opacity"
          >
            {isAr ? 'الحصول على مفتاح' : 'Get Key'} ↗
          </a>
        </div>

        {/* Keys list */}
        <div className="px-3 py-2 space-y-1.5">
          {envKey && (
            <KeyItem
              label={isAr ? '🔒 مفتاح البيئة' : '🔒 Environment Key'}
              keyValue={envKey.key}
              isEnv
              onDelete={() => {}}
              onInspect={(key) => handleTest('env', key)}
              isTesting={testingId === 'env'}
              testResult={testResult?.id === 'env' ? testResult : null}
            />
          )}

          {nonEnvKeys.map((k) => (
            <KeyItem
              key={k.id}
              label={k.label}
              keyValue={k.key}
              onDelete={() => handleDelete(k.id)}
              onInspect={(key) => handleTest(k.id, key)}
              isTesting={testingId === k.id}
              testResult={testResult?.id === k.id ? testResult : null}
            />
          ))}

          {nonEnvKeys.length === 0 && !envKey && (
            <div className="flex items-center gap-1.5 py-2">
              <AlertCircle size={11} className="text-[var(--color-text-muted)]" />
              <span className="text-[10px] text-[var(--color-text-muted)] italic">
                {isAr ? 'لا توجد مفاتيح بعد' : 'No keys configured yet'}
              </span>
            </div>
          )}
        </div>

        {/* Add key form */}
        {isAdding ? (
          <div className="px-3 pb-3 space-y-2">
            <input
              type="password"
              placeholder={isAr ? 'الصق المفتاح هنا...' : 'Paste your API key...'}
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              className="w-full bg-[var(--color-surface-3)] text-[11px] text-[var(--color-text-primary)] px-2.5 py-1.5 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all placeholder:text-[var(--color-text-muted)]"
              autoFocus
            />
            <input
              type="text"
              placeholder={isAr ? 'تسمية (اختياري)' : 'Label (optional)'}
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              className="w-full bg-[var(--color-surface-3)] text-[11px] text-[var(--color-text-primary)] px-2.5 py-1.5 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all placeholder:text-[var(--color-text-muted)]"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleAdd}
                disabled={isSubmitting || !newKey.trim()}
                className="flex-1 flex items-center justify-center gap-1 text-[10px] px-3 py-1.5 rounded-lg bg-[var(--color-accent)] text-white font-medium hover:opacity-90 transition-all disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                {isAr ? 'إضافة' : 'Add'}
              </button>
              <button
                onClick={() => { setIsAdding(false); setNewKey(''); setNewLabel('') }}
                className="flex-1 text-[10px] px-3 py-1.5 rounded-lg bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] border border-[var(--color-border-main)] hover:bg-[var(--color-surface-4)] transition-all"
              >
                {isAr ? 'إلغاء' : 'Cancel'}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setIsAdding(true)}
            className="w-full flex items-center justify-center gap-1.5 text-[10px] py-2 border-t border-[var(--color-border-main)] text-[var(--color-accent)] hover:bg-[var(--color-accent-bg)] transition-all"
          >
            <Plus size={12} />
            {isAr ? 'إضافة مفتاح جديد' : 'Add New Key'}
          </button>
        )}
      </div>

      {/* Inspect Modal */}
      {showInspectModal && (
        <KeyInspectModal
          result={showInspectModal}
          providerIcon={icon}
          onClose={() => setShowInspectModal(null)}
        />
      )}
    </>
  )
}

// ── Key Inspect Modal ────────────────────────────────────────────────────
function KeyInspectModal({
  result,
  providerIcon,
  onClose,
}: {
  result: any
  providerIcon: string
  onClose: () => void
}) {
  const { language } = useAppStore()
  const isAr = language === 'ar'
  const isOk = result.status === 'ok'
  const details = result.details || {}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-2xl border border-[var(--color-border-main)] bg-[var(--color-surface-2)] shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative px-4 pt-4 pb-3 border-b border-[var(--color-border-main)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">{providerIcon}</span>
              <div>
                <span className="text-xs font-bold text-[var(--color-text-primary)]">
                  {isAr ? '🔍 فحص المفتاح' : '🔍 Key Inspection'}
                </span>
                <span className="text-[9px] text-[var(--color-text-muted)] block">
                  {result.provider}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-[var(--color-surface-3)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
            >
              <XCircle size={16} />
            </button>
          </div>
        </div>

        <div className="px-4 py-3 space-y-3 max-h-80 overflow-y-auto">
          {/* Status */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] font-medium ${
            isOk
              ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/20'
              : 'bg-[var(--color-danger-bg)] text-[var(--color-danger)] border border-[var(--color-danger)]/20'
          }`}>
            {isOk ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
            <span>{result.message}</span>
          </div>

          {/* Plan */}
          {details.plan && (
            <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border-main)]">
              <div className="flex items-center gap-1.5">
                <Shield size={11} className="text-[var(--color-accent)]" />
                <span className="text-[10px] text-[var(--color-text-secondary)]">
                  {isAr ? 'الخطة' : 'Plan'}
                </span>
              </div>
              <span className="text-[10px] font-medium text-[var(--color-text-primary)]">{details.plan}</span>
            </div>
          )}

          {/* Remaining credits */}
          {details.remaining && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BarChart3 size={11} className="text-[var(--color-cyan)]" />
                <span className="text-[10px] font-medium text-[var(--color-text-primary)]">
                  {isAr ? 'الرصيد المتبقي' : 'Remaining Credits'}
                </span>
              </div>
              <div className="space-y-1.5">
                {Object.entries(details.remaining).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-[var(--color-surface-3)]/50">
                    <span className="text-[9px] text-[var(--color-text-muted)] capitalize">
                      {key === 'requests' ? (isAr ? 'الطلبات' : 'Requests') : key === 'tokens' ? (isAr ? 'التوكنات' : 'Tokens') : key}
                    </span>
                    <span className="text-[10px] font-mono text-[var(--color-cyan)]">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Limits */}
          {details.limit && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Zap size={11} className="text-[var(--color-warning)]" />
                <span className="text-[10px] font-medium text-[var(--color-text-primary)]">
                  {isAr ? 'حدود الاستخدام' : 'Usage Limits'}
                </span>
              </div>
              <div className="space-y-1.5">
                {Object.entries(details.limit).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-[var(--color-surface-3)]/50">
                    <span className="text-[9px] text-[var(--color-text-muted)] capitalize">
                      {key === 'requests' ? (isAr ? 'الطلبات' : 'Requests') : key === 'tokens' ? (isAr ? 'التوكنات' : 'Tokens') : key}
                    </span>
                    <span className="text-[10px] font-mono text-[var(--color-text-primary)]">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Usage */}
          {details.usage && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BarChart3 size={11} className="text-[var(--color-purple)]" />
                <span className="text-[10px] font-medium text-[var(--color-text-primary)]">
                  {isAr ? 'الاستخدام' : 'Usage'}
                </span>
              </div>
              <div className="space-y-1.5">
                {Object.entries(details.usage).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-[var(--color-surface-3)]/50">
                    <span className="text-[9px] text-[var(--color-text-muted)] capitalize">{key}</span>
                    <span className="text-[10px] text-[var(--color-text-primary)]">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Balance */}
          {details.balance && (
            <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border-main)]">
              <div className="flex items-center gap-1.5">
                <Zap size={11} className="text-[var(--color-warning)]" />
                <span className="text-[10px] text-[var(--color-text-secondary)]">
                  {isAr ? 'الرصيد' : 'Balance'}
                </span>
              </div>
              <span className="text-[10px] font-mono font-bold text-[var(--color-warning)]">{details.balance}</span>
            </div>
          )}

          {/* User info */}
          {details.user && (
            <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border-main)]">
              <div className="flex items-center gap-1.5">
                <ExternalLink size={11} className="text-[var(--color-text-muted)]" />
                <span className="text-[10px] text-[var(--color-text-secondary)]">
                  {isAr ? 'المستخدم' : 'User'}
                </span>
              </div>
              <span className="text-[10px] text-[var(--color-accent)]">{details.user}</span>
            </div>
          )}
        </div>

        {/* Close button */}
        <div className="px-4 py-3 border-t border-[var(--color-border-main)]">
          <button
            onClick={onClose}
            className="w-full text-[10px] py-2 rounded-xl bg-[var(--color-accent)] text-white font-medium hover:opacity-90 transition-all"
          >
            {isAr ? 'إغلاق' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Key Item ──────────────────────────────────────────────────────────────
function KeyItem({
  label,
  keyValue,
  isEnv,
  onDelete,
  onInspect,
  isTesting,
  testResult,
}: {
  label: string
  keyValue: string
  isEnv?: boolean
  onDelete: () => void
  onInspect: (key: string) => void
  isTesting: boolean
  testResult: any
}) {
  const [showKey, setShowKey] = useState(false)
  const { language } = useAppStore()
  const isAr = language === 'ar'
  const masked = keyValue.length > 12 ? keyValue.slice(0, 8) + '••••••••' : keyValue.slice(0, 4) + '••••'

  return (
    <div className={`relative flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-[10px] transition-all ${
      isEnv ? 'bg-[var(--color-accent-bg)]/30 border border-[var(--color-accent)]/10' : 'hover:bg-[var(--color-glass-hover)]'
    }`}>
      {/* Key info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-medium text-[var(--color-text-primary)] truncate">{label}</span>
          {isEnv && (
            <span className="text-[7px] px-1 py-0.5 rounded-full bg-[var(--color-accent-bg)] text-[var(--color-accent)]">ENV</span>
          )}
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          <code className="text-[9px] font-mono text-[var(--color-text-muted)]">{showKey ? keyValue : masked}</code>
          <button
            onClick={() => setShowKey(!showKey)}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
          >
            {showKey ? <EyeOff size={10} /> : <Eye size={10} />}
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Inspect button */}
        {testResult && (
          <span className={`px-1 py-0.5 rounded text-[8px] font-medium ${
            testResult.status === 'ok'
              ? 'text-[var(--color-success)] bg-[var(--color-success)]/10'
              : 'text-[var(--color-danger)] bg-[var(--color-danger-bg)]'
          }`}>
            {testResult.status === 'ok' ? '✓' : '✗'}
          </span>
        )}
        <button
          onClick={() => onInspect(keyValue)}
          disabled={isTesting}
          className="flex items-center gap-1 px-1.5 py-1 rounded-md hover:bg-[var(--color-surface-3)] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-all disabled:opacity-50"
          title={isAr ? 'فحص المفتاح والرصيد' : 'Inspect key & credits'}
        >
          {isTesting ? (
            <Loader2 size={11} className="animate-spin" />
          ) : (
            <Search size={11} />
          )}
          <span className="text-[8px]">{isAr ? 'فحص' : 'Check'}</span>
        </button>

        {/* Delete button */}
        {!isEnv && (
          <button
            onClick={onDelete}
            className="p-1 rounded-md hover:bg-[var(--color-danger-bg)] text-[var(--color-text-muted)] hover:text-[var(--color-danger)] transition-all"
            title="Delete key"
          >
            <Trash2 size={11} />
          </button>
        )}
      </div>
    </div>
  )
}

// ── Stat Bar ──────────────────────────────────────────────────────────────
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
