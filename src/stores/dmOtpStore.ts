// DM OTP Store
// Manages OTP version and key information for Direct Messages

import { OTPVersion, DEFAULT_OTP_VERSION } from '../algorithms/types';

/**
 * DM OTP configuration for a conversation
 */
export interface DMOTPConfig {
    /** The OTP version to use for this conversation */
    otpVersion: OTPVersion;
    /** Current offset in the key stream */
    offset: number;
    /** The raw encryption key */
    rawKey: string;
    /** Timestamp when the config was last updated */
    lastUpdated: number;
}

/**
 * Store for DM OTP configurations
 * Maps conversation IDs to their OTP configurations
 */
class DMOTPStore {
    private configs: Map<string, DMOTPConfig> = new Map();

    /**
     * Get OTP configuration for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @returns OTP configuration or undefined if not set
     */
    getConfig(conversationId: string): DMOTPConfig | undefined {
        return this.configs.get(conversationId);
    }

    /**
     * Set OTP configuration for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @param config OTP configuration
     */
    setConfig(conversationId: string, config: DMOTPConfig): void {
        this.configs.set(conversationId, {
            ...config,
            lastUpdated: Date.now(),
        });
    }

    /**
     * Set just the OTP version for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @param version OTP version to use
     */
    setVersion(conversationId: string, version: OTPVersion): void {
        const existing = this.configs.get(conversationId);
        if (existing) {
            existing.otpVersion = version;
            existing.lastUpdated = Date.now();
        } else {
            this.configs.set(conversationId, {
                otpVersion: version,
                offset: 0,
                rawKey: '',
                lastUpdated: Date.now(),
            });
        }
    }

    /**
     * Get the OTP version for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @returns OTP version or default if not set
     */
    getVersion(conversationId: string): OTPVersion {
        const config = this.configs.get(conversationId);
        return config?.otpVersion ?? DEFAULT_OTP_VERSION;
    }

    /**
     * Set the encryption key for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @param rawKey The raw encryption key
     */
    setKey(conversationId: string, rawKey: string): void {
        const existing = this.configs.get(conversationId);
        if (existing) {
            existing.rawKey = rawKey;
            existing.offset = 0; // Reset offset when key changes
            existing.lastUpdated = Date.now();
        } else {
            this.configs.set(conversationId, {
                otpVersion: DEFAULT_OTP_VERSION,
                offset: 0,
                rawKey,
                lastUpdated: Date.now(),
            });
        }
    }

    /**
     * Get the current offset for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @returns Current offset in key stream
     */
    getOffset(conversationId: string): number {
        const config = this.configs.get(conversationId);
        return config?.offset ?? 0;
    }

    /**
     * Increment the offset for a conversation
     * @param conversationId Unique identifier for the DM conversation
     * @param increment Amount to increment by (message length)
     */
    incrementOffset(conversationId: string, increment: number): void {
        const config = this.configs.get(conversationId);
        if (config) {
            config.offset += increment;
            config.lastUpdated = Date.now();
        }
    }

    /**
     * Reset the offset for a conversation
     * @param conversationId Unique identifier for the DM conversation
     */
    resetOffset(conversationId: string): void {
        const config = this.configs.get(conversationId);
        if (config) {
            config.offset = 0;
            config.lastUpdated = Date.now();
        }
    }

    /**
     * Remove configuration for a conversation
     * @param conversationId Unique identifier for the DM conversation
     */
    removeConfig(conversationId: string): void {
        this.configs.delete(conversationId);
    }

    /**
     * Clear all configurations
     */
    clearAll(): void {
        this.configs.clear();
    }

    /**
     * Get all conversation IDs with configurations
     * @returns Array of conversation IDs
     */
    getAllConversationIds(): string[] {
        return Array.from(this.configs.keys());
    }

    /**
     * Export configurations for persistence
     * @returns Serializable object of all configurations
     */
    exportConfigs(): Record<string, DMOTPConfig> {
        const result: Record<string, DMOTPConfig> = {};
        this.configs.forEach((config, id) => {
            result[id] = { ...config };
        });
        return result;
    }

    /**
     * Import configurations from persistence
     * @param data Serialized configurations
     */
    importConfigs(data: Record<string, DMOTPConfig>): void {
        this.configs.clear();
        for (const [id, config] of Object.entries(data)) {
            this.configs.set(id, { ...config });
        }
    }
}

// Export singleton instance (using only named export for consistency)
export const dmOtpStore = new DMOTPStore();
