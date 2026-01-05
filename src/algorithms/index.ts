// OTP Algorithm Registry
// Central registry for all OTP algorithm versions

import { OTPAlgorithm, OTPVersion, DEFAULT_OTP_VERSION, LATEST_OTP_VERSION, OTP_VERSION_LABELS, OTP_VERSION_DESCRIPTIONS } from './types';
import otpV0Algorithm from './otp_v0';
import otpV1Algorithm from './otp_v1';

// Algorithm registry
const algorithms: Map<OTPVersion, OTPAlgorithm> = new Map([
    ['otp_v0', otpV0Algorithm],
    ['otp_v1', otpV1Algorithm],
]);

/**
 * Get an OTP algorithm by version
 */
export function getAlgorithm(version: OTPVersion): OTPAlgorithm {
    const algorithm = algorithms.get(version);
    if (!algorithm) {
        console.warn(`Unknown OTP version: ${version}, falling back to ${DEFAULT_OTP_VERSION}`);
        const defaultAlgorithm = algorithms.get(DEFAULT_OTP_VERSION);
        if (!defaultAlgorithm) {
            throw new Error(`Default OTP algorithm (${DEFAULT_OTP_VERSION}) is not registered`);
        }
        return defaultAlgorithm;
    }
    return algorithm;
}

/**
 * Get all available OTP versions
 */
export function getAvailableVersions(): OTPVersion[] {
    return Array.from(algorithms.keys());
}

/**
 * Check if a version is valid
 */
export function isValidVersion(version: string): version is OTPVersion {
    return algorithms.has(version as OTPVersion);
}

/**
 * Encrypt a message using the specified OTP version
 */
export function encryptWithVersion(
    message: string,
    rawKey: string,
    offset: number,
    version: OTPVersion = DEFAULT_OTP_VERSION
): string {
    const algorithm = getAlgorithm(version);
    const transformedKey = algorithm.transformKey(rawKey);
    return algorithm.encrypt(message, transformedKey, offset);
}

/**
 * Decrypt a message using the specified OTP version
 */
export function decryptWithVersion(
    encrypted: string,
    rawKey: string,
    offset: number,
    version: OTPVersion = DEFAULT_OTP_VERSION
): string {
    const algorithm = getAlgorithm(version);
    const transformedKey = algorithm.transformKey(rawKey);
    return algorithm.decrypt(encrypted, transformedKey, offset);
}

/**
 * Transform a raw key using the specified OTP version
 */
export function transformKeyWithVersion(
    rawKey: string,
    version: OTPVersion = DEFAULT_OTP_VERSION
): string {
    const algorithm = getAlgorithm(version);
    return algorithm.transformKey(rawKey);
}

// Re-export types and constants
export {
    OTPAlgorithm,
    OTPVersion,
    DEFAULT_OTP_VERSION,
    LATEST_OTP_VERSION,
    OTP_VERSION_LABELS,
    OTP_VERSION_DESCRIPTIONS,
};

// Export individual algorithms
export { otpV0Algorithm, otpV1Algorithm };
