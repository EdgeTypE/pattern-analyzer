// DM History Service
// Service for managing DM conversation history with OTP versioning

import { OTPVersion, DEFAULT_OTP_VERSION } from '../algorithms/types';

/**
 * DM conversation history entry
 */
export interface DMHistoryEntry {
    conversationId: string;
    participantId: string;
    participantName: string;
    otpVersion: OTPVersion;
    lastMessagePreview: string;
    lastMessageTimestamp: number;
    unreadCount: number;
    hasEncryption: boolean;
}

/**
 * Storage key for DM history
 */
const DM_HISTORY_STORAGE_KEY = 'dm_history';

/**
 * DM History Service class
 * Manages conversation history with persistence
 */
class DMHistoryService {
    private history: Map<string, DMHistoryEntry> = new Map();
    private initialized: boolean = false;

    /**
     * Initialize the history service by loading from storage
     */
    initialize(): void {
        if (this.initialized) return;

        try {
            const stored = localStorage.getItem(DM_HISTORY_STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored) as DMHistoryEntry[];
                parsed.forEach(entry => {
                    this.history.set(entry.conversationId, entry);
                });
            }
        } catch (error) {
            console.error('Failed to load DM history:', error);
        }

        this.initialized = true;
    }

    /**
     * Save history to storage
     */
    private saveToStorage(): void {
        try {
            const entries = Array.from(this.history.values());
            localStorage.setItem(DM_HISTORY_STORAGE_KEY, JSON.stringify(entries));
        } catch (error) {
            console.error('Failed to save DM history:', error);
        }
    }

    /**
     * Add or update a conversation in history
     * @param entry History entry to add/update
     */
    addOrUpdate(entry: Partial<DMHistoryEntry> & { conversationId: string }): void {
        const existing = this.history.get(entry.conversationId);
        
        const updated: DMHistoryEntry = {
            conversationId: entry.conversationId,
            participantId: entry.participantId ?? existing?.participantId ?? '',
            participantName: entry.participantName ?? existing?.participantName ?? 'Unknown',
            otpVersion: entry.otpVersion ?? existing?.otpVersion ?? DEFAULT_OTP_VERSION,
            lastMessagePreview: entry.lastMessagePreview ?? existing?.lastMessagePreview ?? '',
            lastMessageTimestamp: entry.lastMessageTimestamp ?? existing?.lastMessageTimestamp ?? Date.now(),
            unreadCount: entry.unreadCount ?? existing?.unreadCount ?? 0,
            hasEncryption: entry.hasEncryption ?? existing?.hasEncryption ?? false,
        };

        this.history.set(entry.conversationId, updated);
        this.saveToStorage();
    }

    /**
     * Update OTP version for a conversation
     * @param conversationId Conversation ID
     * @param otpVersion New OTP version
     */
    updateOTPVersion(conversationId: string, otpVersion: OTPVersion): void {
        const existing = this.history.get(conversationId);
        if (existing) {
            existing.otpVersion = otpVersion;
            this.saveToStorage();
        }
    }

    /**
     * Get a conversation from history
     * @param conversationId Conversation ID
     * @returns History entry or undefined
     */
    get(conversationId: string): DMHistoryEntry | undefined {
        return this.history.get(conversationId);
    }

    /**
     * Get all conversations sorted by last message time
     * @returns Array of history entries
     */
    getAll(): DMHistoryEntry[] {
        return Array.from(this.history.values())
            .sort((a, b) => b.lastMessageTimestamp - a.lastMessageTimestamp);
    }

    /**
     * Get conversations with unread messages
     * @returns Array of entries with unread messages
     */
    getUnread(): DMHistoryEntry[] {
        return this.getAll().filter(entry => entry.unreadCount > 0);
    }

    /**
     * Mark a conversation as read
     * @param conversationId Conversation ID
     */
    markAsRead(conversationId: string): void {
        const entry = this.history.get(conversationId);
        if (entry) {
            entry.unreadCount = 0;
            this.saveToStorage();
        }
    }

    /**
     * Increment unread count for a conversation
     * @param conversationId Conversation ID
     */
    incrementUnread(conversationId: string): void {
        const entry = this.history.get(conversationId);
        if (entry) {
            entry.unreadCount += 1;
            this.saveToStorage();
        }
    }

    /**
     * Remove a conversation from history
     * @param conversationId Conversation ID
     */
    remove(conversationId: string): void {
        this.history.delete(conversationId);
        this.saveToStorage();
    }

    /**
     * Clear all history
     */
    clear(): void {
        this.history.clear();
        this.saveToStorage();
    }

    /**
     * Get total unread count across all conversations
     * @returns Total unread count
     */
    getTotalUnreadCount(): number {
        return Array.from(this.history.values())
            .reduce((sum, entry) => sum + entry.unreadCount, 0);
    }
}

// Export singleton instance
export const dmHistoryService = new DMHistoryService();

export default dmHistoryService;
