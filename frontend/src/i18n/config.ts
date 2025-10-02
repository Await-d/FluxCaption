import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import zhCN from './locales/zh-CN.json'
import en from './locales/en.json'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      'zh-CN': { translation: zhCN },
      en: { translation: en },
    },
    lng: 'zh-CN', // 默认中文
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  })

export default i18n
