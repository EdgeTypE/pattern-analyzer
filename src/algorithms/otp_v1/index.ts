// OTP v1 Algorithm - Enhanced Implementation
// This is the enhanced OTP algorithm with improved key expansion and security

import { OTPAlgorithm, OTPVersion } from '../types';

/**
 * System message threshold - keys larger than this trigger a system message
 */
export const SYSTEM_MESSAGE_KEY_THRESHOLD = 256;

/**
 * Simple hash function for key expansion
 * Uses a basic mixing algorithm to expand short keys
 */
function hashExpand(input: string, targetLength: number): string {
    if (input.length === 0) {
        return '';
    }
    
    // Start with the input repeated to at least target length
    let expanded = input;
    while (expanded.length < targetLength) {
        expanded += input;
    }
    
    // Mix the bytes using a simple algorithm
    const result: number[] = [];
    let accumulator = 0;
    
    for (let i = 0; i < targetLength; i++) {
        const charCode = expanded.charCodeAt(i % expanded.length);
        accumulator = (accumulator + charCode * 31 + i * 17) % 256;
        result.push(accumulator ^ charCode);
    }
    
    return String.fromCharCode(...result);
}

/**
 * Enhanced key transformation with expansion
 * Expands short keys to improve security
 */
function transformKey(rawKey: string): string {
    if (rawKey.length === 0) {
        return '';
    }
    
    // Minimum expanded key length for v1
    const minLength = Math.max(rawKey.length * 4, 1024);
    return hashExpand(rawKey, minLength);
}

/**
 * Enhanced XOR encryption with key stream
 */
function encrypt(message: string, key: string, offset: number): string {
    const result: number[] = [];
    const keyLength = key.length;
    
    if (keyLength === 0) {
        return message;
    }
    
    for (let i = 0; i < message.length; i++) {
        const messageCharCode = message.charCodeAt(i);
        // Use modular arithmetic with offset for key position
        const keyIndex = (offset + i) % keyLength;
        const keyCharCode = key.charCodeAt(keyIndex);
        // Additional mixing step for v1
        const mixedKey = (keyCharCode + i) % 256;
        result.push(messageCharCode ^ mixedKey);
    }
    
    // Convert to base64 for safe transmission
    return btoa(String.fromCharCode(...result));
}

/**
 * Enhanced XOR decryption with key stream
 */
function decrypt(encrypted: string, key: string, offset: number): string {
    const keyLength = key.length;
    
    if (keyLength === 0) {
        return encrypted;
    }
    
    try {
        // Decode from base64
        const decoded = atob(encrypted);
        const result: number[] = [];
        
        for (let i = 0; i < decoded.length; i++) {
            const encryptedCharCode = decoded.charCodeAt(i);
            const keyIndex = (offset + i) % keyLength;
            const keyCharCode = key.charCodeAt(keyIndex);
            // Same mixing step as encryption for v1
            const mixedKey = (keyCharCode + i) % 256;
            result.push(encryptedCharCode ^ mixedKey);
        }
        
        return String.fromCharCode(...result);
    } catch {
        // If decryption fails, return the original encrypted text
        return encrypted;
    }
}

/**
 * Check if key length exceeds the system message threshold
 */
export function shouldShowSystemMessage(keyLength: number): boolean {
    return keyLength > SYSTEM_MESSAGE_KEY_THRESHOLD;
}

/**
 * Generate system message for large keys
 */
export function generateLargeKeySystemMessage(keyLength: number): string {
    return `<system>Şifreleme anahtarı ${keyLength} karakter uzunluğunda. Bu uzun bir anahtar olduğundan, güvenlik artırılmış durumda.</system>`;
}

const otpV1Algorithm: OTPAlgorithm = {
    version: 'otp_v1' as OTPVersion,
    name: 'OTP v1 (Enhanced)',
    description: 'Enhanced OTP encryption with improved key expansion and security',
    transformKey,
    encrypt,
    decrypt,
};

export default otpV1Algorithm;
