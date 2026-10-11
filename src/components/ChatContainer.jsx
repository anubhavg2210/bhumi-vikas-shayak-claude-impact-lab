import React, { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import { translations } from '../i18n/translations';
import { Scale, Sparkles } from 'lucide-react';

export default function ChatContainer({
  messages,
  isLoading,
  language,
  onInspectCitation,
  onRetry
}) {
  const messagesEndRef = useRef(null);
  const t = translations[language];
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);

  // Auto-scroll when messages update or loading starts
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // Cycle through civic loading steps for realistic regulatory feedback
  useEffect(() => {
    if (!isLoading) {
      setLoadingStepIndex(0);
      return;
    }

    const steps = [t.loadingStep1, t.loadingStep2, t.loadingStep3];
    const timer = setInterval(() => {
      setLoadingStepIndex((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 1100);

    return () => clearInterval(timer);
  }, [isLoading, t]);

  const loadingSteps = [t.loadingStep1, t.loadingStep2, t.loadingStep3];

  return (
    <div className="chat-thread-container">
      <div className="container">
        <div className="messages-stream">
          {messages.map((msg, index) => (
            <ChatMessage
              key={index}
              message={msg}
              language={language}
              onInspectCitation={onInspectCitation}
              onRetry={() => onRetry(index)}
            />
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="chat-message-row assistant-row loading-row">
              <div className="message-container assistant-container civic-card loading-card">
                <div className="assistant-header">
                  <div className="assistant-identity">
                    <div className="emblem-avatar shimmer-pulse">
                      <img src="/emblem.svg" alt="MP Emblem" />
                    </div>
                    <div className="identity-text">
                      <span className="assistant-title">{t.assistantResponseLabel}</span>
                      <span className="state-micro">{t.loadingBadge}</span>
                    </div>
                  </div>
                </div>

                <div className="loading-steps-block">
                  <div className="progress-bar-line">
                    <div className="progress-indeterminate" />
                  </div>
                  <div className="step-label-row">
                    <Scale size={16} className="loading-icon-spin" />
                    <span className="current-step-text">
                      {loadingSteps[loadingStepIndex]}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} className="scroll-anchor" />
        </div>
      </div>
    </div>
  );
}
