// OTP Algorithm Type Definitions

/**
 * Supported OTP versions
 */
export type OTPVersion = 'otp_v0' | 'otp_v1';

/**
 * Default OTP version for new DMs
 */
export const DEFAULT_OTP_VERSION: OTPVersion = 'otp_v1';

/**
 * Latest OTP version available
 */
export const LATEST_OTP_VERSION: OTPVersion = 'otp_v1';

/**
 * Human-readable labels for OTP versions
 */
export const OTP_VERSION_LABELS: Record<OTPVersion, string> = {
    otp_v0: 'OTP v0 (Legacy)',
    otp_v1: 'OTP v1 (Enhanced)',
};

/**
 * Descriptions for OTP versions
 */
export const OTP_VERSION_DESCRIPTIONS: Record<OTPVersion, string> = {
    otp_v0: 'Original OTP encryption with basic key transformation',
    otp_v1: 'Enhanced OTP encryption with improved key expansion and security',
};

/**
 * Interface for OTP algorithm implementations
 */
export interface OTPAlgorithm {
    /** Version identifier */
    version: OTPVersion;
    
    /** Display name */
    name: string;
    
    /** Description of the algorithm */
    description: string;
    
    /**
     * Transform a raw key into the algorithm's internal format
     * @param rawKey The original key provided by user
     * @returns Transformed key ready for encryption/decryption
     */
    transformKey(rawKey: string): string;
    
    /**
     * Encrypt a message using the transformed key
     * @param message Plaintext message to encrypt
     * @param key Transformed key (output of transformKey)
     * @param offset Current offset in the key stream
     * @returns Encrypted message
     */
    encrypt(message: string, key: string, offset: number): string;
    
    /**
     * Decrypt a message using the transformed key
     * @param encrypted Encrypted message
     * @param key Transformed key (output of transformKey)
     * @param offset Current offset in the key stream
     * @returns Decrypted plaintext message
     */
    decrypt(encrypted: string, key: string, offset: number): string;
}
