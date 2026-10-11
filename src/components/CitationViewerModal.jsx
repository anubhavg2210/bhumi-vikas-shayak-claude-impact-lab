import React, { useState } from 'react';
import { X, BookOpen, FileText, Copy, Check, ExternalLink, ShieldCheck } from 'lucide-react';
import { translations } from '../i18n/translations';
import { formatRuleLabel } from '../services/citationFormat';

export default function CitationViewerModal({ citation, language, onClose }) {
  const [copied, setCopied] = useState(false);
  const t = translations[language];

  if (!citation) return null;

  const {
    document_title = 'Madhya Pradesh Bhumi Vikas Niyam, 2012',
    rule_number,
    page_number,
    excerpt = '',
    source_url
  } = citation;
  const ruleLabel = formatRuleLabel(rule_number, language);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(
        `${ruleLabel}\n${document_title} (Page ${page_number || 'N/A'})\n\n"${excerpt}"`
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-header-info">
            <span className="badge badge-official">
              <ShieldCheck size={13} />
              <span>{t.modalSourceBadge}</span>
            </span>
            <h3 className="modal-title">{ruleLabel}</h3>
            <p className="modal-subtitle">{document_title}</p>
          </div>

          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label={t.citationCloseModal}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          <div className="modal-meta-row">
            {page_number && (
              <div className="meta-pill">
                <FileText size={14} />
                <span>{t.modalPageNumber}: <strong>{page_number}</strong></span>
              </div>
            )}
            <div className="meta-pill">
              <BookOpen size={14} />
              <span>{t.modalRuleReference}: <strong>{ruleLabel}</strong></span>
            </div>
          </div>

          <div className="modal-passage-section">
            <h4 className="passage-heading">{t.modalFullPassage}</h4>
            <div className="legal-quote full-passage-block">
              {excerpt}
            </div>
          </div>

          <div className="modal-notice-box">
            <p>
              {language === 'hi'
                ? 'यह उद्धरण मध्य प्रदेश नगर तथा ग्राम निवेश विभाग द्वारा विज्ञापित आधिकारिक राजपत्रित नियमों से लिया गया है।'
                : 'This passage is retrieved directly from official gazetted building regulations issued under the MP Town and Country Planning Directorate.'}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button
            type="button"
            className="btn-secondary copy-btn"
            onClick={handleCopy}
          >
            {copied ? <Check size={15} color="#059669" /> : <Copy size={15} />}
            <span>{copied ? t.modalCopied : t.modalCopyExcerpt}</span>
          </button>

          <div className="footer-right-actions">
            {source_url && (
              <a
                href={source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-outline view-pdf-btn"
              >
                <span>PDF Link</span>
                <ExternalLink size={14} />
              </a>
            )}
            <button
              type="button"
              className="btn-primary"
              onClick={onClose}
            >
              {t.citationCloseModal}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
