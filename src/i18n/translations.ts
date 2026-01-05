// i18n Translations
// Translation strings for internationalization

export const translations = {
    tr: {
        // System messages
        largeKeySystemMessage: (keyLength: number) => 
            `<system>Şifreleme anahtarı ${keyLength} karakter uzunluğunda. Bu uzun bir anahtar olduğundan, güvenlik artırılmış durumda.</system>`,
        
        // Encryption status
        encryptionDisabled: 'Şifreleme devre dışı',
        encryptedWith: (algorithmName: string) => `${algorithmName} ile şifreli`,
        
        // UI labels
        advancedSettings: 'Gelişmiş Ayarlar',
        encryptionType: 'Şifreleme Türü',
        encryptionTypeDescription: 'Mesajlarınız için kullanılacak OTP şifreleme sürümünü seçin.',
        encryptionKey: 'Şifreleme Anahtarı',
        encryptionKeyDescription: (threshold: number) => 
            `Mesajları şifrelemek için kullanılacak anahtar. ${threshold} karakterden uzun anahtarlar için sistem bildirimi gösterilir.`,
        keyPlaceholder: 'Şifreleme anahtarını girin...',
        keyLength: (length: number) => `Anahtar uzunluğu: ${length} karakter`,
        largeKeyBadge: 'Büyük Anahtar',
        defaultBadge: 'Varsayılan',
        cancel: 'İptal',
        save: 'Kaydet',
        back: 'Geri',
        send: 'Gönder',
        messagePlaceholder: 'Mesaj yazın...',
    },
    en: {
        // System messages
        largeKeySystemMessage: (keyLength: number) => 
            `<system>Encryption key is ${keyLength} characters long. Security is enhanced due to large key size.</system>`,
        
        // Encryption status
        encryptionDisabled: 'Encryption disabled',
        encryptedWith: (algorithmName: string) => `Encrypted with ${algorithmName}`,
        
        // UI labels
        advancedSettings: 'Advanced Settings',
        encryptionType: 'Encryption Type',
        encryptionTypeDescription: 'Select the OTP encryption version for your messages.',
        encryptionKey: 'Encryption Key',
        encryptionKeyDescription: (threshold: number) => 
            `Key used for message encryption. System notification shown for keys longer than ${threshold} characters.`,
        keyPlaceholder: 'Enter encryption key...',
        keyLength: (length: number) => `Key length: ${length} characters`,
        largeKeyBadge: 'Large Key',
        defaultBadge: 'Default',
        cancel: 'Cancel',
        save: 'Save',
        back: 'Back',
        send: 'Send',
        messagePlaceholder: 'Type a message...',
    },
};

export type Language = keyof typeof translations;
export type TranslationKey = keyof typeof translations.tr;

/**
 * Current language setting
 */
let currentLanguage: Language = 'tr';

/**
 * Set the current language
 */
export function setLanguage(lang: Language): void {
    currentLanguage = lang;
}

/**
 * Get the current language
 */
export function getLanguage(): Language {
    return currentLanguage;
}

/**
 * Get translations for the current language
 */
export function t(): typeof translations.tr {
    return translations[currentLanguage];
}

/**
 * Utility to remove system message tags
 */
export function stripSystemTags(message: string): string {
    return message.replace(/<\/?system>/g, '');
}

export default translations;
