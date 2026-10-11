import React, { useState } from 'react';
import { BookOpen, FileText, ExternalLink, ChevronDown, ChevronUp, Eye } from 'lucide-react';
import { translations } from '../i18n/translations';
import { formatRuleLabel } from '../services/citationFormat';

export default function CitationCard({ citation, index, language, onInspectCitation }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const t = translations[language];

  const {
    document_title = 'Madhya Pradesh Bhumi Vikas Niyam, 2012',
    rule_number,
    page_number,
    excerpt = '',
    source_url
  } = citation;
  const ruleLabel = formatRuleLabel(rule_number, language);

  // Decide if excerpt is long and worth collapsing/expanding
  const isLongExcerpt = excerpt.length > 220;
  const displayedExcerpt = isLongExcerpt && !isExpanded ? `${excerpt.slice(0, 220)}...` : excerpt;

  return (
    <div className="citation-card civic-card">
      {/* Citation Card Header */}
      <div className="citation-header">
        <div className="citation-badge-group">
          <span className="citation-index">#{index + 1}</span>
          <span className="rule-badge">
            <BookOpen size={13} />
            <span>{ruleLabel}</span>
          </span>
          {page_number && (
            <span className="page-badge">
              <FileText size={13} />
              <span>{t.citationPage} {page_number}</span>
            </span>
          )}
        </div>

        {/* Source Opening Controls */}
        <div className="citation-actions">
          <button
            type="button"
            className="btn-outline inspect-source-btn"
            onClick={() => onInspectCitation(citation)}
            title={t.citationViewSource}
          >
            <Eye size={13} />
            <span>{t.citationViewSource}</span>
          </button>

          {source_url && (
            <a
              href={source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-pdf-link"
              title="Open Verified Gazette PDF Document"
            >
              <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>

      {/* Document Title */}
      <div className="citation-doc-title">
        <span className="doc-label">{t.citationDoc}:</span>{' '}
        <strong className="doc-name">{document_title}</strong>
      </div>

      {/* Supporting Legal Passage */}
      <div className="citation-body">
        <blockquote className="legal-quote">
          {displayedExcerpt}
        </blockquote>

        {isLongExcerpt && (
          <button
            type="button"
            className="toggle-excerpt-btn"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span>{isExpanded ? (language === 'hi' ? 'कम पढ़ें' : 'Show Less') : (language === 'hi' ? 'पूरा उद्धरण पढ़ें' : 'Read Full Passage')}</span>
            {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        )}
      </div>
    </div>
  );
}
