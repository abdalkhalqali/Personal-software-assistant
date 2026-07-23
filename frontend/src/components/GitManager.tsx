import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { commitGit } from '../lib/api'
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  ArrowUp,
  ArrowDown,
  FileCode,
  History,
  GitCompareArrows,
  Plus,
  Check,
} from 'lucide-react'

export function GitManager() {
  const { language, gitStatus, setGitStatus } = useAppStore()
  const t = getTranslations(language)
  const [commitMsg, setCommitMsg] = useState('')
  const [status, setStatus] = useState('')

  const handleCommit = async () => {
    if (!commitMsg.trim()) return
    const result = await commitGit(commitMsg)
    setStatus(result)
    setCommitMsg('')

    // Refresh status
    setGitStatus({
      branch: 'main',
      staged: [],
      unstaged: [],
      ahead: 0,
      behind: 0,
    })
  }

  return (
    <div className="py-2 px-3 space-y-3">
      {/* Branch info */}
      <div className="flex items-center justify-between p-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border-main)]">
        <div className="flex items-center gap-2">
          <GitBranch size={14} className="text-[var(--color-accent)]" />
          <span className="text-xs font-mono text-[var(--color-text-primary)]">{gitStatus.branch}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <ArrowUp size={11} /> {gitStatus.ahead}
          </span>
          <span className="flex items-center gap-1">
            <ArrowDown size={11} /> {gitStatus.behind}
          </span>
        </div>
      </div>

      {/* Staged changes */}
      <div>
        <div className="flex items-center gap-1.5 mb-1.5 px-1">
          <Check size={12} className="text-[var(--color-success)]" />
          <span className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            {t.git.staged}
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            ({gitStatus.staged.length})
          </span>
        </div>
        {gitStatus.staged.length === 0 ? (
          <p className="text-[11px] text-[var(--color-text-muted)] px-1">{t.git.noChanges}</p>
        ) : (
          gitStatus.staged.map((file) => (
            <div key={file} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--color-glass-hover)]">
              <FileCode size={12} className="text-[var(--color-success)]" />
              <span className="text-xs text-[var(--color-text-primary)]">{file}</span>
            </div>
          ))
        )}
      </div>

      {/* Unstaged changes */}
      <div>
        <div className="flex items-center gap-1.5 mb-1.5 px-1">
          <Plus size={12} className="text-[var(--color-warning)]" />
          <span className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            {t.git.unstaged}
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            ({gitStatus.unstaged.length})
          </span>
        </div>
        {gitStatus.unstaged.map((file) => (
          <div key={file} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--color-glass-hover)]">
            <FileCode size={12} className="text-[var(--color-warning)]" />
            <span className="text-xs text-[var(--color-text-primary)]">{file}</span>
          </div>
        ))}
      </div>

      {/* Commit */}
      <div className="space-y-2">
        <input
          type="text"
          value={commitMsg}
          onChange={(e) => setCommitMsg(e.target.value)}
          placeholder={t.git.commitMessage}
          className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] px-3 py-2 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={handleCommit}
            disabled={!commitMsg.trim()}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-[var(--color-accent-bg)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 disabled:opacity-50 transition-all"
          >
            <GitCommit size={13} />
            {t.git.commit}
          </button>
          <button className="p-2 rounded-xl hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] transition-all">
            <GitPullRequest size={14} />
          </button>
          <button className="p-2 rounded-xl hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] transition-all">
            <ArrowUp size={14} />
          </button>
          <button className="p-2 rounded-xl hover:bg-[var(--color-glass-hover)] text-[var(--color-text-muted)] transition-all">
            <ArrowDown size={14} />
          </button>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)] transition-all">
          <GitCompareArrows size={12} />
          {t.git.diff}
        </button>
        <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)] transition-all">
          <History size={12} />
          {t.git.history}
        </button>
      </div>

      {status && (
        <div className="text-[11px] text-[var(--color-success)] px-1">{status}</div>
      )}
    </div>
  )
}
