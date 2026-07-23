import { useAppStore, type Message } from '../stores/appStore'

const API_BASE = '/api'

export async function sendMessage(
  messages: Message[],
  onToken: (token: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void,
) {
  const store = useAppStore.getState()
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
    })

    if (!response.ok) {
      const err = await response.text()
      onError(err)
      return
    }

    if (!response.body) {
      onError('No response body')
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
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
    onDone(fullText)
  } catch (err: any) {
    onError(err.message || 'Connection error')
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
