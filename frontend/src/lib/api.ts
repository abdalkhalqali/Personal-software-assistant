import { useAppStore, type Message } from '../stores/appStore'

const API_BASE = '/api'

export async function sendMessage(
  messages: Message[],
  onToken: (token: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
) {
  const store = useAppStore.getState()
  let fullText = ''

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000) // 60s overall timeout

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          mode: store.agentMode,
          temperature: store.temperature,
          max_tokens: store.maxTokens,
        }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const err = await response.text()
        onError(err)
        return
      }

      // Read the entire response as text - avoids proxy streaming issues
      const text = await response.text()

      // Parse SSE events from the full text
      let sseBuffer = ''
      for (const ch of text) {
        sseBuffer += ch
        if (sseBuffer.endsWith('\n\n')) {
          // We have a complete SSE event
          const lines = sseBuffer.trim().split('\n')
          sseBuffer = ''

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data: ')) continue

            const data = trimmed.slice(6).trim()
            if (data === '[DONE]') {
              onDone(fullText)
              return
            }

            try {
              const parsed = JSON.parse(data)
              if (parsed.token) {
                fullText += parsed.token
                onToken(parsed.token)
              }
              if (parsed.done) {
                onDone(fullText)
                return
              }
              if (parsed.error) {
                onError(parsed.error)
                return
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      // Process any remaining data in buffer
      if (sseBuffer.trim().startsWith('data: ')) {
        try {
          const parsed = JSON.parse(sseBuffer.trim().slice(6).trim())
          if (parsed.token) {
            fullText += parsed.token
            onToken(parsed.token)
          }
        } catch {
          // ignore
        }
      }

      onDone(fullText)
    } finally {
      clearTimeout(timeoutId)
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      onDone(fullText)
    } else {
      onError(err.message || 'Connection error')
    }
  }
}

export async function executeCommand(command: string): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/terminal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
    const data = await response.json()
    return data.output || data.error || 'No output'
  } catch (err: any) {
    return `Error: ${err.message}`
  }
}

export async function getProjectFiles(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/files`)
    const data = await response.json()
    return data.files || []
  } catch {
    return []
  }
}

export async function getGitStatus(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/git/status`)
    return await response.json()
  } catch {
    return null
  }
}

export async function commitGit(message: string): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/git/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    const data = await response.json()
    return data.message || 'Committed'
  } catch (err: any) {
    return `Error: ${err.message}`
  }
}
