export type ThemeId = 'noon' | 'twilight' | 'dawn' | 'sakura'

export interface ThemeColors {
  name: string
  nameEn: string
  emoji: string
  surface: string
  surface2: string
  surface3: string
  surface4: string
  borderMain: string
  borderHover: string
  textPrimary: string
  textSecondary: string
  textMuted: string
  accent: string
  accentHover: string
  accentBg: string
  success: string
  warning: string
  danger: string
  dangerBg: string
  purple: string
  pink: string
  cyan: string
  codeBg: string
  terminalBg: string
  glassBg: string
  glassBorder: string
  glassHover: string
  gradientFrom: string
  gradientTo: string
  glowColor: string
}

export const themes: Record<ThemeId, ThemeColors> = {
  // 🌹 Noon — Rose & Gold: دافئ ورومانسي فاخر
  noon: {
    name: 'ورود',
    nameEn: 'Noon',
    emoji: '🌹',
    surface: '#1a0f14',
    surface2: '#24151c',
    surface3: '#2d1a23',
    surface4: '#3d2230',
    borderMain: '#4a2a38',
    borderHover: '#6a3d50',
    textPrimary: '#f5e1e8',
    textSecondary: '#d4a0b5',
    textMuted: '#a07085',
    accent: '#ff8fab',
    accentHover: '#ffa8c5',
    accentBg: 'rgba(255, 143, 171, 0.12)',
    success: '#7bc96a',
    warning: '#f0b34b',
    danger: '#ff6b6b',
    dangerBg: 'rgba(255, 107, 107, 0.12)',
    purple: '#d4a0ff',
    pink: '#ff8fab',
    cyan: '#8ad4c8',
    codeBg: '#1f1219',
    terminalBg: '#0d070a',
    glassBg: 'rgba(36, 21, 28, 0.7)',
    glassBorder: 'rgba(255, 143, 171, 0.15)',
    glassHover: 'rgba(255, 143, 171, 0.1)',
    gradientFrom: '#ff8fab',
    gradientTo: '#d4a0ff',
    glowColor: 'rgba(255, 143, 171, 0.3)',
  },

  // 🌆 Twilight — Purple & Magenta: غامض وساحر
  twilight: {
    name: 'شفق',
    nameEn: 'Twilight',
    emoji: '🌆',
    surface: '#0f0a1a',
    surface2: '#19122e',
    surface3: '#231a3d',
    surface4: '#2e234d',
    borderMain: '#3f2f5e',
    borderHover: '#5a4278',
    textPrimary: '#e8defa',
    textSecondary: '#b8a0e0',
    textMuted: '#7a6095',
    accent: '#b388ff',
    accentHover: '#cc9fff',
    accentBg: 'rgba(179, 136, 255, 0.12)',
    success: '#69c48a',
    warning: '#e8b84a',
    danger: '#ff6b9d',
    dangerBg: 'rgba(255, 107, 157, 0.12)',
    purple: '#b388ff',
    pink: '#ff80b0',
    cyan: '#80d8ff',
    codeBg: '#140e24',
    terminalBg: '#080512',
    glassBg: 'rgba(25, 18, 46, 0.7)',
    glassBorder: 'rgba(179, 136, 255, 0.15)',
    glassHover: 'rgba(179, 136, 255, 0.1)',
    gradientFrom: '#b388ff',
    gradientTo: '#ff80b0',
    glowColor: 'rgba(179, 136, 255, 0.3)',
  },

  // 🌅 Dawn — Peach & Coral: مشرق ومبهج دافئ
  dawn: {
    name: 'فجر',
    nameEn: 'Dawn',
    emoji: '🌅',
    surface: '#1a120e',
    surface2: '#241a14',
    surface3: '#2f221b',
    surface4: '#3d2d24',
    borderMain: '#4e3a2d',
    borderHover: '#6a5040',
    textPrimary: '#f5e8dc',
    textSecondary: '#d4b8a0',
    textMuted: '#a08070',
    accent: '#ff9f7c',
    accentHover: '#ffb89a',
    accentBg: 'rgba(255, 159, 124, 0.12)',
    success: '#7bc96a',
    warning: '#f0b34b',
    danger: '#ff6b5a',
    dangerBg: 'rgba(255, 107, 90, 0.12)',
    purple: '#d4a0ff',
    pink: '#ff9f7c',
    cyan: '#8ad4c8',
    codeBg: '#1e1510',
    terminalBg: '#0c0806',
    glassBg: 'rgba(36, 26, 20, 0.7)',
    glassBorder: 'rgba(255, 159, 124, 0.15)',
    glassHover: 'rgba(255, 159, 124, 0.1)',
    gradientFrom: '#ff9f7c',
    gradientTo: '#f7c978',
    glowColor: 'rgba(255, 159, 124, 0.3)',
  },

  // 🌸 Sakura — Cherry Blossom: ناعم وحالم
  sakura: {
    name: 'ساكورا',
    nameEn: 'Sakura',
    emoji: '🌸',
    surface: '#120f14',
    surface2: '#1d1820',
    surface3: '#282230',
    surface4: '#352e40',
    borderMain: '#453c50',
    borderHover: '#5f5268',
    textPrimary: '#ece4f0',
    textSecondary: '#c4b0d0',
    textMuted: '#8a7895',
    accent: '#f0a0d0',
    accentHover: '#f8b8e0',
    accentBg: 'rgba(240, 160, 208, 0.12)',
    success: '#80d0a8',
    warning: '#d4b060',
    danger: '#f080a0',
    dangerBg: 'rgba(240, 128, 160, 0.12)',
    purple: '#c8a0f0',
    pink: '#f0a0d0',
    cyan: '#a0d8e8',
    codeBg: '#18141e',
    terminalBg: '#0a0810',
    glassBg: 'rgba(29, 24, 32, 0.7)',
    glassBorder: 'rgba(240, 160, 208, 0.15)',
    glassHover: 'rgba(240, 160, 208, 0.1)',
    gradientFrom: '#f0a0d0',
    gradientTo: '#a0d8e8',
    glowColor: 'rgba(240, 160, 208, 0.3)',
  },
}

export function applyTheme(themeId: ThemeId) {
  const theme = themes[themeId]
  const root = document.documentElement

  const vars: [string, string][] = [
    ['--color-surface', theme.surface],
    ['--color-surface-2', theme.surface2],
    ['--color-surface-3', theme.surface3],
    ['--color-surface-4', theme.surface4],
    ['--color-border-main', theme.borderMain],
    ['--color-border-hover', theme.borderHover],
    ['--color-text-primary', theme.textPrimary],
    ['--color-text-secondary', theme.textSecondary],
    ['--color-text-muted', theme.textMuted],
    ['--color-accent', theme.accent],
    ['--color-accent-hover', theme.accentHover],
    ['--color-accent-bg', theme.accentBg],
    ['--color-success', theme.success],
    ['--color-warning', theme.warning],
    ['--color-danger', theme.danger],
    ['--color-danger-bg', theme.dangerBg],
    ['--color-purple', theme.purple],
    ['--color-pink', theme.pink],
    ['--color-cyan', theme.cyan],
    ['--color-code-bg', theme.codeBg],
    ['--color-terminal-bg', theme.terminalBg],
    ['--color-glass', theme.glassBg],
    ['--color-glass-border', theme.glassBorder],
    ['--color-glass-hover', theme.glassHover],
  ]

  vars.forEach(([key, val]) => {
    root.style.setProperty(key, val)
  })
}
