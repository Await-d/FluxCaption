import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import zhCN from './locales/zh-CN.json'
import en from './locales/en.json'

const savedLanguage = typeof window !== 'undefined' ? window.localStorage.getItem('i18nextLng') : null
const browserLanguage = typeof navigator !== 'undefined' ? navigator.language : 'zh-CN'
const initialLanguage = savedLanguage === 'en' || savedLanguage === 'zh-CN'
  ? savedLanguage
  : browserLanguage.startsWith('zh')
    ? 'zh-CN'
    : 'en'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      'zh-CN': { translation: zhCN },
      en: { translation: en },
    },
    lng: initialLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  })

if (typeof document !== 'undefined') {
  document.documentElement.lang = i18n.language
  i18n.on('languageChanged', (lng) => {
    document.documentElement.lang = lng
  })
}

export default i18n
