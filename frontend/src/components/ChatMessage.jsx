import React from 'react';
import { User, ShieldCheck, Calendar, Info, AlertCircle, RotateCcw } from 'lucide-react';
import CitationCard from './CitationCard';
import InsufficientEvidenceAlert from './InsufficientEvidenceAlert';
import { translations } from '../i18n/translations';

export default function ChatMessage({
  message,
  language,
  onInspectCitation,
  onRetry
}) {
  const t = translations[language];
  const { role, content, citations = [], confidence, insufficient_evidence, document_coverage_date, isError } = message;

  if (role === 'user') {
    return (
      <div className="chat-message-row user-row">
        <div className="message-container user-container">
          <div className="message-header-meta">
            <span className="sender-tag user-tag">
              <User size={13} />
              <span>{t.userQueryLabel}</span>
            </span>
          </div>
          <div className="user-bubble">
            <p className="user-query-text">{content}</p>
          </div>
        </div>
      </div>
    );
  }

  // Assistant / Regulatory response
  const getConfidenceBadge = () => {
    if (insufficient_evidence || confidence === 'insufficient') {
      return (
        <span className="badge badge-insufficient">
          {t.confidenceInsufficient}
        </span>
      );
    }
    if (confidence === 'high') {
      return (
        <span className="badge badge-high">
          {t.confidenceHigh}
        </span>
      );
    }
    if (confidence === 'medium') {
      return (
        <span className="badge badge-medium">
          {t.confidenceMedium}
        </span>
      );
    }
    return (
      <span className="badge badge-low">
        {t.confidenceLow}
      </span>
    );
  };

  // Helper to format text with paragraphs, bullet points, and bold tags
  const renderFormattedAnswer = (text) => {
    if (!text) return null;
    const paragraphs = text.split('\n\n');

    return paragraphs.map((para, pIdx) => {
      // Check if paragraph is list items
      if (para.includes('\n* ') || para.includes('\n1. ') || para.startsWith('* ') || para.startsWith('1. ')) {
        const lines = para.split('\n');
        return (
          <div key={pIdx} className="answer-list-block">
            {lines.map((line, lIdx) => {
              const cleanLine = line.replace(/^[\*\-]\s+/, '').replace(/^\d+\.\s+/, '');
              const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
              const isNumbered = /^\d+\.\s+/.test(line);

              return (
                <div key={lIdx} className="list-item-row">
                  <span className="bullet-indicator">{isNumbered ? line.match(/^\d+\./)[0] : '•'}</span>
                  <span className="line-content">
                    {parts.map((part, partIdx) => {
                      if (part.startsWith('**') && part.endsWith('**')) {
                        return <strong key={partIdx}>{part.slice(2, -2)}</strong>;
                      }
                      return part;
                    })}
                  </span>
                </div>
              );
            })}
          </div>
        );
      }

      // Regular paragraph with bold text parsing
      const parts = para.split(/(\*\*.*?\*\*)/g);
      return (
        <p key={pIdx} className="answer-paragraph">
          {parts.map((part, partIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={partIdx}>{part.slice(2, -2)}</strong>;
            }
            return part;
          })}
        </p>
      );
    });
  };

  return (
    <div className="chat-message-row assistant-row">
      <div className="message-container assistant-container civic-card">
        {/* Assistant Header with emblem and status badges */}
        <div className="assistant-header">
          <div className="assistant-identity">
            <div className="emblem-avatar">
              <img src="/emblem.svg" alt="MP Emblem" />
            </div>
            <div className="identity-text">
              <span className="assistant-title">{t.assistantResponseLabel}</span>
              <span className="state-micro">Madhya Pradesh Bhumi Vikas Niyam, 2012</span>
            </div>
          </div>

          <div className="assistant-badges">
            {getConfidenceBadge()}
            {document_coverage_date && (
              <span className="coverage-date-badge" title="Verified against database date">
                <Calendar size={12} />
                <span>As of {document_coverage_date}</span>
              </span>
            )}
          </div>
        </div>

        {/* Error State */}
        {isError ? (
          <div className="message-error-state">
            <div className="error-icon-box">
              <AlertCircle size={20} color="#b91c1c" />
            </div>
            <div className="error-content">
              <p className="error-message-text">{content}</p>
              {onRetry && (
                <button type="button" className="btn-secondary retry-btn" onClick={onRetry}>
                  <RotateCcw size={14} />
                  <span>{t.retryButton}</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="assistant-body">
            {/* If insufficient evidence, display special alert callout */}
            {insufficient_evidence ? (
              <div className="insufficient-wrap">
                <div className="primary-response-text">
                  {renderFormattedAnswer(content)}
                </div>
                <InsufficientEvidenceAlert language={language} />
              </div>
            ) : (
              <>
                {/* AI Explanation / Synthesized guidance */}
                <div className="explanation-section">
                  <div className="explanation-header">
                    <Info size={15} className="explanation-icon" />
                    <span>Statutory Analysis</span>
                  </div>
                  <div className="primary-response-text">
                    {renderFormattedAnswer(content)}
                  </div>
                </div>

                {/* Legal Citations Section */}
                {citations && citations.length > 0 && (
                  <div className="citations-section">
                    <div className="citations-header">
                      <div className="citations-title-wrap">
                        <ShieldCheck size={16} className="citations-icon" />
                        <h4 className="citations-title">{t.citationsHeading}</h4>
                      </div>
                      <span className="citations-count-pill">
                        {citations.length} {citations.length === 1 ? 'Citation' : 'Citations'}
                      </span>
                    </div>

                    <div className="citations-grid">
                      {citations.map((citation, cIdx) => (
                        <CitationCard
                          key={cIdx}
                          citation={citation}
                          index={cIdx}
                          language={language}
                          onInspectCitation={onInspectCitation}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Regulatory Footer Disclaimer */}
            <div className="message-statutory-disclaimer">
              <p>
                <strong>Statutory Notice:</strong> Information extracted directly from MP Bhumi Vikas Niyam, 2012. Citizen applications must be verified with the competent Municipal Corporation / T&CP planning authority prior to commencement of physical construction.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
