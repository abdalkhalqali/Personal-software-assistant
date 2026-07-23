import { create } from 'zustand'
import type { Language } from '../i18n'

export type AgentMode = 'architect' | 'developer' | 'debugger' | 'reviewer' | 'security' | 'teacher'
export type ThemeMode = 'dark' | 'light'
export type SidebarPanel = 'project' | 'agent' | 'memory' | 'terminal' | 'git' | 'model' | 'workspace' | null

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  codeBlocks?: CodeBlock[]
  isStreaming?: boolean
}

export interface CodeBlock {
  id: string
  language: string
  filename?: string
  code: string
  applied?: boolean
  rejected?: boolean
}

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'folder'
  size?: number
  children?: FileNode[]
}

export interface GitStatus {
  branch: string
  staged: string[]
  unstaged: string[]
  ahead: number
  behind: number
}

export interface SystemStats {
  cpu: number
  gpu: number
  ram: number
  responseTime: number
}

interface AppState {
  // Language
  language: Language
  setLanguage: (lang: Language) => void

  // Sidebar
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  activePanel: SidebarPanel
  setActivePanel: (panel: SidebarPanel) => void

  // Chat
  messages: Message[]
  addMessage: (msg: Message) => void
  updateMessage: (id: string, updates: Partial<Message>) => void
  clearMessages: () => void
  isStreaming: boolean
  setStreaming: (streaming: boolean) => void

  // Agent mode
  agentMode: AgentMode
  setAgentMode: (mode: AgentMode) => void

  // File explorer
  files: FileNode[]
  setFiles: (files: FileNode[]) => void
  selectedFile: string | null
  setSelectedFile: (path: string | null) => void

  // Git
  gitStatus: GitStatus
  setGitStatus: (status: GitStatus) => void

  // Model settings
  temperature: number
  setTemperature: (temp: number) => void
  maxTokens: number
  setMaxTokens: (tokens: number) => void
  systemStats: SystemStats
  setSystemStats: (stats: SystemStats) => void

  // Workspace
  projectName: string
  setProjectName: (name: string) => void
  programmingLanguage: string
  setProgrammingLanguage: (lang: string) => void
  framework: string
  setFramework: (fw: string) => void
  autoSave: boolean
  setAutoSave: (save: boolean) => void
  fontSize: number
  setFontSize: (size: number) => void

  // Terminal
  terminalHistory: string[]
  addTerminalLine: (line: string) => void
  clearTerminal: () => void

  // Memory
  showMemory: boolean
  memoryContent: string
  setMemoryContent: (content: string) => void
  updateMemory: () => void
  deleteMemory: () => void
  reanalyzeProject: () => void
}

export const useAppStore = create<AppState>((set) => ({
  // Language
  language: 'ar',
  setLanguage: (lang) => {
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
    set({ language: lang })
  },

  // Sidebar
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  activePanel: null,
  setActivePanel: (panel) => set((s) => ({
    activePanel: s.activePanel === panel ? null : panel,
    sidebarOpen: true,
  })),

  // Chat
  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateMessage: (id, updates) => set((s) => ({
    messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
  })),
  clearMessages: () => set({ messages: [] }),
  isStreaming: false,
  setStreaming: (streaming) => set({ isStreaming: streaming }),

  // Agent mode
  agentMode: 'developer',
  setAgentMode: (mode) => set({ agentMode: mode }),

  // File explorer
  files: [],
  setFiles: (files) => set({ files }),
  selectedFile: null,
  setSelectedFile: (path) => set({ selectedFile: path }),

  // Git
  gitStatus: { branch: 'main', staged: [], unstaged: [], ahead: 0, behind: 0 },
  setGitStatus: (status) => set({ gitStatus: status }),

  // Model settings
  temperature: 0.7,
  setTemperature: (temp) => set({ temperature: temp }),
  maxTokens: 3072,
  setMaxTokens: (tokens) => set({ maxTokens: tokens }),
  systemStats: { cpu: 0, gpu: 0, ram: 0, responseTime: 0 },
  setSystemStats: (stats) => set({ systemStats: stats }),

  // Workspace
  projectName: 'مساعد البرمجة الشخصي',
  setProjectName: (name) => set({ projectName: name }),
  programmingLanguage: 'Python',
  setProgrammingLanguage: (lang) => set({ programmingLanguage: lang }),
  framework: 'Gradio',
  setFramework: (fw) => set({ framework: fw }),
  autoSave: true,
  setAutoSave: (save) => set({ autoSave: save }),
  fontSize: 14,
  setFontSize: (size) => set({ fontSize: size }),

  // Terminal
  terminalHistory: ['$ System Ready | Personal AI Coding Agent v3.0'],
  addTerminalLine: (line) => set((s) => ({
    terminalHistory: [...s.terminalHistory, line],
  })),
  clearTerminal: () => set({ terminalHistory: [] }),

  // Memory
  showMemory: false,
  memoryContent: '',
  setMemoryContent: (content) => set({ memoryContent: content }),
  updateMemory: () => set((s) => ({ memoryContent: s.memoryContent })),
  deleteMemory: () => set({ memoryContent: '' }),
  reanalyzeProject: () => {},
}))
