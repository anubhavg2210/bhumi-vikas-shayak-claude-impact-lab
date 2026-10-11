import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Scale, BookMarked, Globe, CornerDownLeft } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function DashboardHero({ language, onSubmitQuery, isLoading }) {
  const [query, setQuery] = useState('');
  const [validationError, setValidationError] = useState('');
  const textareaRef = useRef(null);
  const t = translations[language];

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [query]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) {
      setValidationError(t.errorEmpty);
      return;
    }
    setValidationError('');
    onSubmitQuery(query.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <section className="dashboard-hero">
      <div className="container">
        <div className="hero-content">
          {/* Main Headline & Regulatory Intro */}
          <div className="hero-header">
            <div className="civic-seal-badge">
              <Scale size={16} className="seal-icon" />
              <span>Directorate of Town & Country Planning (T&CP) MP Compliance</span>
            </div>
            
            <h2 className="hero-title">{t.heroTitle}</h2>
            <p className="hero-description">{t.heroDescription}</p>
          </div>

          {/* Primary Main Question Input Box */}
          <div className="hero-search-wrapper">
            <form onSubmit={handleSubmit} className="hero-search-box civic-card">
              <div className="input-textarea-row">
                <textarea
                  ref={textareaRef}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    if (validationError) setValidationError('');
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder={t.inputPlaceholder}
                  rows={2}
                  disabled={isLoading}
                  className="hero-textarea"
                  aria-label="Ask about MP building regulations"
                />
              </div>

              {validationError && (
                <div className="validation-error-banner" role="alert">
                  {validationError}
                </div>
              )}

              <div className="hero-search-footer">
                <div className="keyboard-hints">
                  <span className="hint-pill">
                    <CornerDownLeft size={12} />
                    <span>{t.inputHelpHint}</span>
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !query.trim()}
                  className="btn-primary submit-inquiry-btn"
                >
                  {isLoading ? (
                    <>
                      <span className="spinner-sm" />
                      <span>{t.loadingBadge}...</span>
                    </>
                  ) : (
                    <>
                      <span>{t.inputButtonText}</span>
                      <Send size={15} />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Key Assurance Metric Cards */}
          <div className="hero-metrics-grid">
            <div className="metric-card civic-card">
              <div className="metric-icon-box">
                <Scale size={20} />
              </div>
              <div className="metric-info">
                <span className="metric-value">{t.statRulesCoveredVal}</span>
                <span className="metric-label">{t.statRulesCovered}</span>
              </div>
            </div>

            <div className="metric-card civic-card">
              <div className="metric-icon-box">
                <BookMarked size={20} />
              </div>
              <div className="metric-info">
                <span className="metric-value">{t.statCitationsVal}</span>
                <span className="metric-label">{t.statCitations}</span>
              </div>
            </div>

            <div className="metric-card civic-card">
              <div className="metric-icon-box">
                <Globe size={20} />
              </div>
              <div className="metric-info">
                <span className="metric-value">{t.statLanguageVal}</span>
                <span className="metric-label">{t.statLanguage}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
