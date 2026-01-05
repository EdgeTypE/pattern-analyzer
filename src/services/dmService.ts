// DM Service
// Service for handling Direct Message encryption and decryption with OTP versioning

import { 
    encryptWithVersion, 
    decryptWithVersion, 
    OTPVersion, 
    DEFAULT_OTP_VERSION,
    getAlgorithm 
} from '../algorithms';
import { dmOtpStore, DMOTPConfig } from '../stores/dmOtpStore';
import { shouldShowSystemMessage, generateLargeKeySystemMessage, SYSTEM_MESSAGE_KEY_THRESHOLD } from '../algorithms/otp_v1';
import { t } from '../i18n';

/**
 * Message structure for DM
 */
export interface DMMessage {
    id: string;
    senderId: string;
    content: string;
    encryptedContent?: string;
    timestamp: number;
    isSystemMessage?: boolean;
}

/**
 * DM conversation structure
 */
export interface DMConversation {
    id: string;
    participantIds: string[];
    otpVersion: OTPVersion;
    lastMessageTimestamp: number;
}

/**
 * DM Service class
 * Handles encryption/decryption of DM messages with OTP versioning
 */
class DMService {
    /**
     * Initialize a DM conversation with OTP settings
     * @param conversationId Unique identifier for the conversation
     * @param rawKey Encryption key
     * @param otpVersion OTP version to use (default: otp_v1)
     * @returns System message if key is large, otherwise undefined
     */
    initializeConversation(
        conversationId: string,
        rawKey: string,
        otpVersion: OTPVersion = DEFAULT_OTP_VERSION
    ): DMMessage | undefined {
        // Store the configuration
        dmOtpStore.setConfig(conversationId, {
            otpVersion,
            offset: 0,
            rawKey,
            lastUpdated: Date.now(),
        });

        // Check if we should show a system message for large keys
        if (shouldShowSystemMessage(rawKey.length)) {
            return {
                id: `system-${Date.now()}`,
                senderId: 'system',
                content: generateLargeKeySystemMessage(rawKey.length, t().largeKeySystemMessage),
                timestamp: Date.now(),
                isSystemMessage: true,
            };
        }

        return undefined;
    }

    /**
     * Update OTP version for a conversation
     * @param conversationId Unique identifier for the conversation
     * @param otpVersion New OTP version
     */
    updateOTPVersion(conversationId: string, otpVersion: OTPVersion): void {
        dmOtpStore.setVersion(conversationId, otpVersion);
    }

    /**
     * Update encryption key for a conversation
     * @param conversationId Unique identifier for the conversation
     * @param rawKey New encryption key
     * @returns System message if key is large, otherwise undefined
     */
    updateKey(conversationId: string, rawKey: string): DMMessage | undefined {
        dmOtpStore.setKey(conversationId, rawKey);

        // Check if we should show a system message for large keys
        if (shouldShowSystemMessage(rawKey.length)) {
            return {
                id: `system-${Date.now()}`,
                senderId: 'system',
                content: generateLargeKeySystemMessage(rawKey.length, t().largeKeySystemMessage),
                timestamp: Date.now(),
                isSystemMessage: true,
            };
        }

        return undefined;
    }

    /**
     * Encrypt a message for sending
     * @param conversationId Unique identifier for the conversation
     * @param plaintext Message to encrypt
     * @returns Encrypted message content (or plaintext if no encryption configured)
     */
    encryptMessage(conversationId: string, plaintext: string): string {
        const config = dmOtpStore.getConfig(conversationId);
        
        if (!config || !config.rawKey) {
            // No encryption configured - log warning and return plaintext
            console.warn(`No encryption configured for conversation ${conversationId}. Message will be sent unencrypted.`);
            return plaintext;
        }

        const encrypted = encryptWithVersion(
            plaintext,
            config.rawKey,
            config.offset,
            config.otpVersion
        );

        // Increment offset by message length
        dmOtpStore.incrementOffset(conversationId, plaintext.length);

        return encrypted;
    }

    /**
     * Decrypt a received message
     * @param conversationId Unique identifier for the conversation
     * @param encrypted Encrypted message content
     * @param messageLength Original message length (for offset calculation)
     * @returns Decrypted plaintext (or original text if no encryption configured)
     */
    decryptMessage(conversationId: string, encrypted: string, messageLength: number): string {
        const config = dmOtpStore.getConfig(conversationId);
        
        if (!config || !config.rawKey) {
            // No encryption configured - message may be unencrypted plaintext
            console.warn(`No encryption configured for conversation ${conversationId}. Returning message as-is.`);
            return encrypted;
        }

        const decrypted = decryptWithVersion(
            encrypted,
            config.rawKey,
            config.offset,
            config.otpVersion
        );

        // Increment offset by message length
        dmOtpStore.incrementOffset(conversationId, messageLength);

        return decrypted;
    }

    /**
     * Get the current OTP configuration for a conversation
     * @param conversationId Unique identifier for the conversation
     * @returns Current OTP configuration
     */
    getConfig(conversationId: string): DMOTPConfig | undefined {
        return dmOtpStore.getConfig(conversationId);
    }

    /**
     * Get the OTP version for a conversation
     * @param conversationId Unique identifier for the conversation
     * @returns Current OTP version
     */
    getOTPVersion(conversationId: string): OTPVersion {
        return dmOtpStore.getVersion(conversationId);
    }

    /**
     * Check if the conversation has encryption enabled
     * @param conversationId Unique identifier for the conversation
     * @returns True if encryption is configured
     */
    hasEncryption(conversationId: string): boolean {
        const config = dmOtpStore.getConfig(conversationId);
        return config !== undefined && config.rawKey.length > 0;
    }

    /**
     * Get encryption status description
     * @param conversationId Unique identifier for the conversation
     * @returns Human-readable encryption status
     */
    getEncryptionStatus(conversationId: string): string {
        const config = dmOtpStore.getConfig(conversationId);
        
        if (!config || !config.rawKey) {
            return t().encryptionDisabled;
        }

        const algorithm = getAlgorithm(config.otpVersion);
        return t().encryptedWith(algorithm.name);
    }

    /**
     * Check if key is large enough to show system message
     * @param keyLength Length of the encryption key
     * @returns True if key is above threshold
     */
    isLargeKey(keyLength: number): boolean {
        return shouldShowSystemMessage(keyLength);
    }

    /**
     * Get the key threshold for system messages
     * @returns Threshold value
     */
    getKeyThreshold(): number {
        return SYSTEM_MESSAGE_KEY_THRESHOLD;
    }

    /**
     * Reset encryption for a conversation
     * @param conversationId Unique identifier for the conversation
     */
    resetEncryption(conversationId: string): void {
        dmOtpStore.removeConfig(conversationId);
    }

    /**
     * Reset offset for a conversation (for resync)
     * @param conversationId Unique identifier for the conversation
     */
    resetOffset(conversationId: string): void {
        dmOtpStore.resetOffset(conversationId);
    }
}

// Export singleton instance (using only named export for consistency)
export const dmService = new DMService();
