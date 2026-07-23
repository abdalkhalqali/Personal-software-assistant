import { ar } from './ar'
import { en } from './en'

export type TranslationKeys = typeof ar
export type Language = 'ar' | 'en'

const translations: Record<Language, TranslationKeys> = { ar, en }

export function getTranslations(lang: Language): TranslationKeys {
  return translations[lang]
}

export function t(key: string, lang: Language): string {
  const keys = key.split('.')
  let value: any = translations[lang]
  for (const k of keys) {
    value = value?.[k]
  }
  return typeof value === 'string' ? value : key
}
