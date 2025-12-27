import en from './en.json';
import es from './es.json';

export const languages = {
    en: 'English',
    es: 'Español'
};

export const defaultLang = 'en';

export const translations = { en, es } as const;

export type Language = keyof typeof translations;

export function getLangFromUrl(url: URL): Language {
    const [, lang] = url.pathname.split('/');
    if (lang in translations) return lang as Language;
    return defaultLang;
}

export function useTranslations(lang: Language) {
    return function t<K extends keyof typeof en>(key: K): (typeof en)[K] {
        return translations[lang][key] ?? translations[defaultLang][key];
    };
}

export function getLocalizedPath(path: string, lang: Language): string {
    return `/${lang}${path.startsWith('/') ? path : `/${path}`}`;
}
