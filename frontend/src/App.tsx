import { useEffect } from 'react'
import { TopNavbar } from './components/TopNavbar'
import { Sidebar } from './components/Sidebar'
import { ChatArea } from './components/ChatArea'
import { SmartInputBar } from './components/SmartInputBar'
import { KeyboardShortcutsModal, useKeyboardShortcuts } from './components/KeyboardShortcuts'
import { useAppStore } from './stores/appStore'
import { applyTheme } from './lib/themes'

export default function App() {
  const { language, themeId } = useAppStore()
  useKeyboardShortcuts()

  // Initialize language direction
  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = language
    document.title = language === 'ar'
      ? 'وكيل البرمجة الذكي — مساعد البرمجة بالذكاء الاصطناعي'
      : 'AI Coding Agent — AI Programming Assistant'
  }, [language])

  // Apply theme
  useEffect(() => {
    applyTheme(themeId)
  }, [themeId])

  return (
    <div className="h-screen flex flex-col bg-[var(--color-surface)] overflow-hidden transition-colors duration-500">
      {/* Top Navbar */}
      <TopNavbar />

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <ChatArea />
          <SmartInputBar />
        </div>

        {/* Sidebar */}
        <Sidebar />
      </div>

      {/* Keyboard shortcuts modal */}
      <KeyboardShortcutsModal />
    </div>
  )
}
