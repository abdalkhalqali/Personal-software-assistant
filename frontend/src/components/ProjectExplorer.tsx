import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { getTranslations } from '../i18n'
import { cn, formatBytes } from '../lib/utils'
import {
  Folder,
  FolderOpen,
  File,
  FileCode,
  FileJson,
  FileText,
  Image,
  Search,
  Plus,
  Upload,
} from 'lucide-react'

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'py': return <FileCode size={14} className="text-[#3572A5]" />
    case 'js': return <FileCode size={14} className="text-[#f7df1e]" />
    case 'ts':
    case 'tsx': return <FileCode size={14} className="text-[#3178c6]" />
    case 'jsx': return <FileCode size={14} className="text-[#61dafb]" />
    case 'html': return <FileCode size={14} className="text-[#e34c26]" />
    case 'css': return <FileCode size={14} className="text-[#563d7c]" />
    case 'json': return <FileJson size={14} className="text-[#5B5BD6]" />
    case 'md': return <FileText size={14} className="text-[#083fa1]" />
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg': return <Image size={14} className="text-[#7c3aed]" />
    default: return <File size={14} className="text-[var(--color-text-muted)]" />
  }
}

function FileTreeNode({ name, path, type, children, size, depth = 0 }: any) {
  const [expanded, setExpanded] = useState(false)
  const { selectedFile, setSelectedFile } = useAppStore()
  const isSelected = selectedFile === path

  return (
    <div>
      <button
        onClick={() => {
          if (type === 'folder') setExpanded(!expanded)
          else setSelectedFile(path)
        }}
        className={cn(
          'w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg transition-all duration-150',
          isSelected
            ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)]',
        )}
        style={{ paddingInlineStart: `${12 + depth * 16}px` }}
      >
        {type === 'folder' ? (
          expanded ? (
            <FolderOpen size={14} className="text-[var(--color-warning)] shrink-0" />
          ) : (
            <Folder size={14} className="text-[var(--color-warning)] shrink-0" />
          )
        ) : (
          getFileIcon(name)
        )}
        <span className="truncate flex-1 text-start">{name}</span>
        {size !== undefined && (
          <span className="text-[10px] text-[var(--color-text-muted)]">{formatBytes(size)}</span>
        )}
      </button>
      {type === 'folder' && expanded && children && (
        <div>
          {children.map((child: any) => (
            <FileTreeNode key={child.path} {...child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function ProjectExplorer() {
  const { language } = useAppStore()
  const t = getTranslations(language)
  const [searchQuery, setSearchQuery] = useState('')

  const sampleFiles = [
    {
      name: 'المشروع', path: '/', type: 'folder',
      children: [
        { name: 'app.py', path: '/app.py', type: 'file', size: 2840 },
        { name: 'web_demo_mm.py', path: '/web_demo_mm.py', type: 'file', size: 14230 },
        { name: 'requirements.txt', path: '/requirements.txt', type: 'file', size: 120 },
        { name: 'requirements_web_demo.txt', path: '/requirements_web_demo.txt', type: 'file', size: 180 },
        { name: 'README.md', path: '/README.md', type: 'file', size: 850 },
        {
          name: 'evaluation', path: '/evaluation', type: 'folder',
          children: [
            { name: 'MathVision', path: '/evaluation/MathVision', type: 'folder', children: [] },
            { name: 'mmmu', path: '/evaluation/mmmu', type: 'folder', children: [] },
          ],
        },
        {
          name: 'qwen-vl-utils', path: '/qwen-vl-utils', type: 'folder',
          children: [
            { name: 'README.md', path: '/qwen-vl-utils/README.md', type: 'file', size: 5600 },
          ],
        },
        {
          name: 'frontend', path: '/frontend', type: 'folder',
          children: [
            { name: 'package.json', path: '/frontend/package.json', type: 'file', size: 400 },
            { name: 'vite.config.ts', path: '/frontend/vite.config.ts', type: 'file', size: 300 },
            {
              name: 'src', path: '/frontend/src', type: 'folder',
              children: [
                { name: 'App.tsx', path: '/frontend/src/App.tsx', type: 'file', size: 2000 },
                { name: 'index.css', path: '/frontend/src/index.css', type: 'file', size: 5000 },
              ],
            },
          ],
        },
      ],
    },
  ]

  return (
    <div className="py-2">
      {/* Search */}
      <div className="relative px-3 mb-2">
        <Search size={13} className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t.sidebar.searchFiles}
          className="w-full bg-[var(--color-surface-3)] text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] px-3 py-1.5 pr-8 rounded-lg border border-[var(--color-border-main)] outline-none focus:border-[var(--color-accent)]/50 transition-all"
        />
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1 px-3 mb-2">
        <button className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)] transition-all">
          <Plus size={12} />
          {t.sidebar.newFile}
        </button>
        <button className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)] transition-all">
          <Upload size={12} />
          {t.sidebar.uploadFile}
        </button>
      </div>

      {/* File tree */}
      <div className="space-y-0.5">
        {sampleFiles.map((node) => (
          <FileTreeNode key={node.path} {...node} />
        ))}
      </div>
    </div>
  )
}
