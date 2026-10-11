import React, { useState } from 'react';
import { ShieldAlert, BookOpen, ChevronDown, ChevronUp, Calendar } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function RegulatoryNoticeBanner({ language }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const t = translations[language];

  return (
    <aside className="regulatory-banner" aria-label="Statutory Coverage Notice">
      <div className="container">
        <div className="banner-card">
          <div className="banner-primary">
            <div className="banner-icon-area">
              <ShieldAlert className="banner-icon" size={20} />
            </div>

            <div className="banner-text-area">
              <div className="banner-headline">
                <strong className="banner-title">{t.bannerCoverageTitle}:</strong>{' '}
                <span className="banner-desc">{t.bannerCoverageText}</span>
              </div>
              
              <div className="banner-meta">
                <span className="coverage-date-pill">
                  <Calendar size={13} />
                  <span>{t.bannerCoverageDateLabel}: <strong>{t.bannerCoverageDate}</strong></span>
                </span>
                <span className="coverage-rules-pill">
                  <BookOpen size={13} />
                  <span>M.P. Nagar Tatha Gram Nivesh Adhiniyam, 1973</span>
                </span>
              </div>
            </div>

            <div className="banner-action-area">
              <button
                type="button"
                className="banner-toggle-btn"
                onClick={() => setIsExpanded(!isExpanded)}
                aria-expanded={isExpanded}
              >
                <span>{isExpanded ? (language === 'hi' ? 'कम देखें' : 'Hide Disclaimer') : (language === 'hi' ? 'विधिक अस्वीकरण' : 'Legal Disclaimer')}</span>
                {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
              </button>
            </div>
          </div>

          {isExpanded && (
            <div className="banner-extended-content">
              <p className="banner-disclaimer-text">
                {t.bannerDisclaimer}
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
