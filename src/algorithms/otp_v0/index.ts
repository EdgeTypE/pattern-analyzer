// OTP v0 Algorithm - Legacy Implementation
// This is the original OTP algorithm with basic key transformation

import { OTPAlgorithm, OTPVersion } from '../types';

/**
 * Simple XOR-based encryption using key stream
 */
function xorEncrypt(message: string, key: string, offset: number): string {
    const result: number[] = [];
    const keyLength = key.length;
    
    if (keyLength === 0) {
        return message;
    }
    
    for (let i = 0; i < message.length; i++) {
        const messageCharCode = message.charCodeAt(i);
        const keyIndex = (offset + i) % keyLength;
        const keyCharCode = key.charCodeAt(keyIndex);
        result.push(messageCharCode ^ keyCharCode);
    }
    
    // Convert to base64 for safe transmission
    return btoa(String.fromCharCode(...result));
}

/**
 * Simple XOR-based decryption using key stream
 */
function xorDecrypt(encrypted: string, key: string, offset: number): string {
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
            result.push(encryptedCharCode ^ keyCharCode);
        }
        
        return String.fromCharCode(...result);
    } catch {
        // If decryption fails, return an empty string to avoid leaking encryption format info
        console.warn('Decryption failed in OTP v0');
        return '';
    }
}

/**
 * Basic key transformation - just returns the key as-is
 */
function transformKey(rawKey: string): string {
    return rawKey;
}

const otpV0Algorithm: OTPAlgorithm = {
    version: 'otp_v0' as OTPVersion,
    name: 'OTP v0 (Legacy)',
    description: 'Original OTP encryption with basic key transformation',
    transformKey,
    encrypt: xorEncrypt,
    decrypt: xorDecrypt,
};

export default otpV0Algorithm;
