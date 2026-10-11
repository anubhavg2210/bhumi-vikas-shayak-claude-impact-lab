import React from 'react';
import { Languages, RotateCcw, Server, Cpu, ExternalLink, Moon, Sun, Volume2, VolumeX } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function Header({
  language,
  onLanguageChange,
  onClearSession,
  isMockMode,
  onToggleMockMode,
  hasMessages,
  onOpenCoverageNotice,
  theme,
  onToggleTheme,
  canSpeak,
  isMuted,
  onToggleMute
}) {
  const t = translations[language];

  return (
    <header className="site-header">
      <div className="header-inner container">
        {/* Brand Identity */}
        <div className="brand-group">
          <div className="emblem-wrapper">
            <img src="/emblem.svg" alt="MP State Regulatory Emblem" className="brand-emblem" />
          </div>
          <div className="brand-titles">
            <div className="brand-topline">
              <span className="brand-state">{t.stateAffiliation}</span>
              <span className="badge badge-official">{t.badgeOfficial}</span>
            </div>
            <h1 className="brand-name">
              {t.appTitle}
              <span className="brand-name-hi">
                {language === 'en' ? ' • भूमि विकास सहायक' : ' • Bhumi Vikas Sahayak'}
              </span>
            </h1>
          </div>
        </div>

        {/* Action Controls */}
        <div className="header-actions">
          {/* Mock/Live Environment Toggle */}
          <button
            type="button"
            className={`btn-outline status-toggle ${isMockMode ? 'is-mock' : 'is-live'}`}
            onClick={onToggleMockMode}
            title={isMockMode ? t.apiSwitchToLive : t.apiSwitchToMock}
            aria-label="Toggle backend or mock data source"
          >
            {isMockMode ? (
              <>
                <Cpu size={14} className="status-icon mock" />
                <span className="status-text">{t.apiStatusMock}</span>
              </>
            ) : (
              <>
                <Server size={14} className="status-icon live" />
                <span className="status-text">{t.apiStatusOnline}</span>
              </>
            )}
          </button>

          {/* Language Switcher */}
          <button
            type="button"
            className="btn-secondary lang-toggle"
            onClick={() => onLanguageChange(language === 'en' ? 'hi' : 'en')}
            aria-label="Change language to Hindi or English"
          >
            <Languages size={15} />
            <span className="lang-target-label">{t.langToggle}</span>
          </button>

          {/* Mute spoken answers */}
          {canSpeak && (
            <button
              type="button"
              className={`btn-outline icon-toggle mute-toggle ${isMuted ? 'is-muted' : ''}`}
              onClick={onToggleMute}
              title={isMuted ? t.unmuteVoice : t.muteVoice}
              aria-label={isMuted ? t.unmuteVoice : t.muteVoice}
              aria-pressed={isMuted}
            >
              {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>
          )}

          {/* Light / dark theme */}
          <button
            type="button"
            className="btn-outline icon-toggle theme-toggle"
            onClick={onToggleTheme}
            title={theme === 'dark' ? t.themeLight : t.themeDark}
            aria-label={theme === 'dark' ? t.themeLight : t.themeDark}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* New Inquiry / Reset (visible if conversation is active) */}
          {hasMessages && (
            <button
              type="button"
              className="btn-outline clear-btn"
              onClick={onClearSession}
              title={t.clearHistory}
            >
              <RotateCcw size={14} />
              <span className="clear-text">{t.clearHistory}</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
