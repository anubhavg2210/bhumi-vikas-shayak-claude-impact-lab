import React from 'react';
import { FileSearch, AlertTriangle, Quote } from 'lucide-react';
import { translations } from '../i18n/translations';

const METHOD_KEYS = { text_layer: 'documentMethodText', ocr: 'documentMethodOcr', plain_text: 'documentMethodPlain' };

/** What the backend read from an uploaded document, plus verified quotes from it. */
export default function DocumentReadSummary({ document, quotes = [], language }) {
  const t = translations[language];
  if (!document) return null;

  const methods = (document.extraction_methods || []).map((m) => t[METHOD_KEYS[m]] || m).join(', ');

  return (
    <div className="document-read-card" data-testid="document-read-summary">
      <div className="document-read-header">
        <FileSearch size={16} />
        <span className="document-read-title">{t.documentReadTitle}</span>
        <strong className="document-read-name">{document.filename}</strong>
      </div>

      <div className="document-read-meta">
        <span className="meta-pill">
          {t.documentPages.replace('{read}', document.pages_read).replace('{total}', document.pages_total)}
        </span>
        {methods && <span className="meta-pill">{methods}</span>}
      </div>

      {document.ocr_is_generative && (
        <p className="document-read-note">
          <AlertTriangle size={13} />
          <span>{t.documentOcrWarning}</span>
        </p>
      )}

      {document.warnings && document.warnings.length > 0 && (
        <ul className="document-read-warnings">
          {document.warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}

      {quotes.length > 0 && (
        <div className="document-quotes">
          <div className="document-quotes-heading">
            <Quote size={13} />
            <span>{t.documentQuotesHeading}</span>
          </div>
          <ul>
            {quotes.map((q, i) => (
              <li key={i}>
                <span className="doc-quote-page">{t.citationPage} {q.page}</span>
                <span className="doc-quote-text">“{q.quote}”</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
