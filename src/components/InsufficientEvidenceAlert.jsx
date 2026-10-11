import React from 'react';
import { AlertTriangle, HelpCircle, ArrowRight, ShieldAlert, Building } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function InsufficientEvidenceAlert({ language }) {
  const t = translations[language];

  return (
    <div className="insufficient-evidence-card" role="alert">
      <div className="alert-top">
        <div className="alert-icon-wrap">
          <AlertTriangle size={22} className="alert-icon" />
        </div>
        <div className="alert-heading-block">
          <h4 className="alert-title">{t.insufficientTitle}</h4>
          <p className="alert-description">{t.insufficientDescription}</p>
        </div>
      </div>

      <div className="alert-details-grid">
        {/* Reasons */}
        <div className="alert-subcard">
          <div className="subcard-title">
            <HelpCircle size={15} />
            <span>{t.insufficientReasonsHeader}</span>
          </div>
          <ul className="reasons-list">
            <li>{t.insufficientReason1}</li>
            <li>{t.insufficientReason2}</li>
            <li>{t.insufficientReason3}</li>
          </ul>
        </div>

        {/* Actionable next steps */}
        <div className="alert-subcard action-subcard">
          <div className="subcard-title">
            <Building size={15} />
            <span>{t.insufficientActionHeading}</span>
          </div>
          <p className="action-text">{t.insufficientActionText}</p>
          <div className="action-links">
            <a
              href="https://tcpm.mp.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="tcp-link"
            >
              <span>Directorate of Town & Country Planning (T&CP) MP</span>
              <ArrowRight size={13} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
