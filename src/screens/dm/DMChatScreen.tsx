// DM Chat Screen
// Direct Message chat screen with OTP versioning support and advanced settings

import React, { useState, useCallback, useMemo } from 'react';
import { 
    OTPVersion, 
    DEFAULT_OTP_VERSION, 
    OTP_VERSION_LABELS, 
    OTP_VERSION_DESCRIPTIONS,
    getAvailableVersions 
} from '../../algorithms';
import { dmService, DMMessage } from '../../services/dmService';
import { t, stripSystemTags } from '../../i18n';

/**
 * Props for DMChatScreen component
 */
interface DMChatScreenProps {
    conversationId: string;
    participantName: string;
    onBack?: () => void;
}

/**
 * Props for Advanced Settings Modal
 */
interface AdvancedSettingsProps {
    isOpen: boolean;
    onClose: () => void;
    conversationId: string;
    currentVersion: OTPVersion;
    currentKey: string;
    onVersionChange: (version: OTPVersion) => void;
    onKeyChange: (key: string) => void;
}

/**
 * Advanced Settings Modal Component
 */
const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({
    isOpen,
    onClose,
    conversationId,
    currentVersion,
    currentKey,
    onVersionChange,
    onKeyChange,
}) => {
    const [selectedVersion, setSelectedVersion] = useState<OTPVersion>(currentVersion);
    const [encryptionKey, setEncryptionKey] = useState(currentKey);
    const availableVersions = useMemo(() => getAvailableVersions(), []);

    const handleSave = useCallback(() => {
        if (selectedVersion !== currentVersion) {
            onVersionChange(selectedVersion);
        }
        if (encryptionKey !== currentKey) {
            onKeyChange(encryptionKey);
        }
        onClose();
    }, [selectedVersion, currentVersion, encryptionKey, currentKey, onVersionChange, onKeyChange, onClose]);

    if (!isOpen) return null;

    const translations = t();

    return (
        <div className="advanced-settings-modal">
            <div className="modal-overlay" onClick={onClose} />
            <div className="modal-content">
                <h2>{translations.advancedSettings}</h2>
                
                <div className="settings-section">
                    <h3>{translations.encryptionType}</h3>
                    <p className="section-description">
                        {translations.encryptionTypeDescription}
                    </p>
                    
                    <div className="version-selector">
                        {availableVersions.map((version) => (
                            <div 
                                key={version}
                                className={`version-option ${selectedVersion === version ? 'selected' : ''}`}
                                onClick={() => setSelectedVersion(version)}
                            >
                                <div className="version-header">
                                    <input
                                        type="radio"
                                        name="otpVersion"
                                        checked={selectedVersion === version}
                                        onChange={() => setSelectedVersion(version)}
                                    />
                                    <span className="version-label">{OTP_VERSION_LABELS[version]}</span>
                                    {version === DEFAULT_OTP_VERSION && (
                                        <span className="default-badge">{translations.defaultBadge}</span>
                                    )}
                                </div>
                                <p className="version-description">{OTP_VERSION_DESCRIPTIONS[version]}</p>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="settings-section">
                    <h3>{translations.encryptionKey}</h3>
                    <p className="section-description">
                        {translations.encryptionKeyDescription(dmService.getKeyThreshold())}
                    </p>
                    
                    <div className="key-input-container">
                        <textarea
                            className="key-input"
                            value={encryptionKey}
                            onChange={(e) => setEncryptionKey(e.target.value)}
                            placeholder={translations.keyPlaceholder}
                            rows={3}
                        />
                        <div className="key-info">
                            <span>{translations.keyLength(encryptionKey.length)}</span>
                            {dmService.isLargeKey(encryptionKey.length) && (
                                <span className="large-key-badge">{translations.largeKeyBadge}</span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="modal-actions">
                    <button className="cancel-button" onClick={onClose}>
                        {translations.cancel}
                    </button>
                    <button className="save-button" onClick={handleSave}>
                        {translations.save}
                    </button>
                </div>
            </div>

            <style>{`
                .advanced-settings-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .modal-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                }

                .modal-content {
                    position: relative;
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    max-width: 500px;
                    width: 90%;
                    max-height: 90vh;
                    overflow-y: auto;
                    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
                }

                .modal-content h2 {
                    margin: 0 0 20px;
                    font-size: 20px;
                    color: #1a1a1a;
                }

                .settings-section {
                    margin-bottom: 24px;
                }

                .settings-section h3 {
                    margin: 0 0 8px;
                    font-size: 16px;
                    color: #333;
                }

                .section-description {
                    margin: 0 0 12px;
                    font-size: 14px;
                    color: #666;
                }

                .version-selector {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .version-option {
                    padding: 12px;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .version-option:hover {
                    border-color: #0066cc;
                }

                .version-option.selected {
                    border-color: #0066cc;
                    background: #f0f7ff;
                }

                .version-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 4px;
                }

                .version-label {
                    font-weight: 600;
                    color: #1a1a1a;
                }

                .default-badge {
                    background: #0066cc;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                }

                .version-description {
                    margin: 0;
                    font-size: 13px;
                    color: #666;
                    margin-left: 24px;
                }

                .key-input-container {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .key-input {
                    width: 100%;
                    padding: 12px;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    font-family: monospace;
                    font-size: 14px;
                    resize: vertical;
                }

                .key-input:focus {
                    outline: none;
                    border-color: #0066cc;
                }

                .key-info {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    font-size: 13px;
                    color: #666;
                }

                .large-key-badge {
                    background: #28a745;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                }

                .modal-actions {
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                    margin-top: 24px;
                }

                .cancel-button {
                    padding: 10px 20px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background: white;
                    cursor: pointer;
                    font-size: 14px;
                }

                .cancel-button:hover {
                    background: #f5f5f5;
                }

                .save-button {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 8px;
                    background: #0066cc;
                    color: white;
                    cursor: pointer;
                    font-size: 14px;
                }

                .save-button:hover {
                    background: #0052a3;
                }
            `}</style>
        </div>
    );
};

/**
 * DM Chat Screen Component
 */
const DMChatScreen: React.FC<DMChatScreenProps> = ({
    conversationId,
    participantName,
    onBack,
}) => {
    const [messages, setMessages] = useState<DMMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
    
    // Get current encryption config
    const config = dmService.getConfig(conversationId);
    const currentVersion = config?.otpVersion ?? DEFAULT_OTP_VERSION;
    const currentKey = config?.rawKey ?? '';
    const encryptionStatus = dmService.getEncryptionStatus(conversationId);

    const handleSendMessage = useCallback(() => {
        if (!inputText.trim()) return;

        const encrypted = dmService.encryptMessage(conversationId, inputText);
        
        const newMessage: DMMessage = {
            id: `msg-${Date.now()}`,
            senderId: 'self',
            content: inputText,
            encryptedContent: encrypted,
            timestamp: Date.now(),
        };

        setMessages(prev => [...prev, newMessage]);
        setInputText('');
    }, [conversationId, inputText]);

    const handleVersionChange = useCallback((version: OTPVersion) => {
        dmService.updateOTPVersion(conversationId, version);
    }, [conversationId]);

    const handleKeyChange = useCallback((key: string) => {
        const systemMessage = dmService.updateKey(conversationId, key);
        if (systemMessage) {
            setMessages(prev => [...prev, systemMessage]);
        }
    }, [conversationId]);

    const translations = t();

    return (
        <div className="dm-chat-screen">
            <header className="chat-header">
                {onBack && (
                    <button className="back-button" onClick={onBack}>
                        ← {translations.back}
                    </button>
                )}
                <div className="header-info">
                    <h1>{participantName}</h1>
                    <span className="encryption-status">{encryptionStatus}</span>
                </div>
                <button 
                    className="settings-button"
                    onClick={() => setShowAdvancedSettings(true)}
                >
                    ⚙️ {translations.advancedSettings}
                </button>
            </header>

            <div className="messages-container">
                {messages.map(message => (
                    <div 
                        key={message.id} 
                        className={`message ${message.isSystemMessage ? 'system' : message.senderId === 'self' ? 'sent' : 'received'}`}
                    >
                        {message.isSystemMessage ? (
                            <div className="system-message">
                                {stripSystemTags(message.content)}
                            </div>
                        ) : (
                            <div className="message-content">{message.content}</div>
                        )}
                        <span className="message-time">
                            {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                    </div>
                ))}
            </div>

            <div className="input-container">
                <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder={translations.messagePlaceholder}
                    className="message-input"
                />
                <button onClick={handleSendMessage} className="send-button">
                    {translations.send}
                </button>
            </div>

            <AdvancedSettings
                isOpen={showAdvancedSettings}
                onClose={() => setShowAdvancedSettings(false)}
                conversationId={conversationId}
                currentVersion={currentVersion}
                currentKey={currentKey}
                onVersionChange={handleVersionChange}
                onKeyChange={handleKeyChange}
            />

            <style>{`
                .dm-chat-screen {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    background: #f5f5f5;
                }

                .chat-header {
                    display: flex;
                    align-items: center;
                    padding: 16px;
                    background: white;
                    border-bottom: 1px solid #e0e0e0;
                    gap: 16px;
                }

                .back-button {
                    padding: 8px 12px;
                    border: none;
                    background: transparent;
                    cursor: pointer;
                    font-size: 16px;
                }

                .header-info {
                    flex: 1;
                }

                .header-info h1 {
                    margin: 0;
                    font-size: 18px;
                    color: #1a1a1a;
                }

                .encryption-status {
                    font-size: 12px;
                    color: #666;
                }

                .settings-button {
                    padding: 8px 16px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background: white;
                    cursor: pointer;
                    font-size: 14px;
                }

                .settings-button:hover {
                    background: #f5f5f5;
                }

                .messages-container {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .message {
                    max-width: 70%;
                    padding: 12px;
                    border-radius: 12px;
                }

                .message.sent {
                    align-self: flex-end;
                    background: #0066cc;
                    color: white;
                }

                .message.received {
                    align-self: flex-start;
                    background: white;
                    border: 1px solid #e0e0e0;
                }

                .message.system {
                    align-self: center;
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    max-width: 90%;
                }

                .system-message {
                    font-size: 13px;
                    color: #856404;
                    text-align: center;
                }

                .message-content {
                    margin-bottom: 4px;
                }

                .message-time {
                    font-size: 11px;
                    opacity: 0.7;
                }

                .input-container {
                    display: flex;
                    padding: 16px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    gap: 12px;
                }

                .message-input {
                    flex: 1;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 24px;
                    font-size: 14px;
                }

                .message-input:focus {
                    outline: none;
                    border-color: #0066cc;
                }

                .send-button {
                    padding: 12px 24px;
                    border: none;
                    border-radius: 24px;
                    background: #0066cc;
                    color: white;
                    cursor: pointer;
                    font-size: 14px;
                }

                .send-button:hover {
                    background: #0052a3;
                }
            `}</style>
        </div>
    );
};

export default DMChatScreen;
