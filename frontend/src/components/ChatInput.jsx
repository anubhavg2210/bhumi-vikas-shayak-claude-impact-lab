import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles, AlertCircle } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function ChatInput({ language, onSendMessage, isLoading }) {
  const [inputText, setInputText] = useState('');
  const [validationError, setValidationError] = useState('');
  const textareaRef = useRef(null);
  const t = translations[language];

  // Auto-resize textarea height as text increases
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [inputText]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed) {
      setValidationError(t.errorEmpty);
      if (textareaRef.current) textareaRef.current.focus();
      return;
    }

    if (isLoading) return; // Prevent duplicate submission

    setValidationError('');
    onSendMessage(trimmed);
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-input-sticky-container">
      <div className="container">
        <form onSubmit={handleSubmit} className="chat-input-card civic-card">
          {validationError && (
            <div className="input-validation-msg" role="alert">
              <AlertCircle size={14} />
              <span>{validationError}</span>
            </div>
          )}

          <div className="chat-input-box">
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                if (validationError) setValidationError('');
              }}
              onKeyDown={handleKeyDown}
              placeholder={t.inputPlaceholder}
              disabled={isLoading}
              className="chat-textarea"
              aria-label="Enter question regarding MP building bylaws"
            />

            <button
              type="submit"
              disabled={isLoading || !inputText.trim()}
              className="btn-primary chat-send-btn"
              title={t.inputButtonText}
              aria-label="Send inquiry"
            >
              {isLoading ? (
                <span className="spinner-sm" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </div>

          <div className="chat-input-hints-bar">
            <span className="kbd-shortcut-hint">
              <CornerDownLeft size={11} />
              <span>{t.inputHelpHint}</span>
            </span>

            <span className="character-counter">
              {inputText.length} characters
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
