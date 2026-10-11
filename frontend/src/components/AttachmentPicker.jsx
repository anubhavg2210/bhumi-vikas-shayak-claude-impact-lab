import React, { useRef } from 'react';
import { Paperclip, X, FileText } from 'lucide-react';
import { translations } from '../i18n/translations';
import { ACCEPTED_UPLOAD_EXTENSIONS, MAX_UPLOAD_BYTES, checkUploadFile } from '../services/chatApi';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Attach-a-document control: paperclip button, hidden file input, and the selected-file chip.
 * Validates type and size before the file is accepted.
 */
export default function AttachmentPicker({ language, file, onFileChange, onError, disabled }) {
  const inputRef = useRef(null);
  const t = translations[language];
  const maxMb = Math.round(MAX_UPLOAD_BYTES / (1024 * 1024));

  const handleChange = (e) => {
    const picked = e.target.files && e.target.files[0];
    e.target.value = ''; // allow re-selecting the same file
    if (!picked) return;
    const problem = checkUploadFile(picked);
    if (problem) {
      onError(t[problem].replace('{mb}', maxMb));
      return;
    }
    onError('');
    onFileChange(picked);
  };

  return (
    <div className="attachment-picker">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_UPLOAD_EXTENSIONS.join(',')}
        onChange={handleChange}
        className="visually-hidden-input"
        data-testid="document-file-input"
        aria-label={t.attachDocument}
        tabIndex={-1}
      />
      {file ? (
        <span className="attachment-chip" title={file.name}>
          <FileText size={13} />
          <span className="attachment-name">{file.name}</span>
          <span className="attachment-size">{formatSize(file.size)}</span>
          <button
            type="button"
            className="attachment-remove"
            onClick={() => onFileChange(null)}
            disabled={disabled}
            aria-label={t.removeAttachment}
          >
            <X size={12} />
          </button>
        </span>
      ) : (
        <button
          type="button"
          className="btn-outline attach-btn"
          onClick={() => inputRef.current && inputRef.current.click()}
          disabled={disabled}
          title={t.attachHint.replace('{mb}', maxMb)}
        >
          <Paperclip size={14} />
          <span>{t.attachDocument}</span>
        </button>
      )}
    </div>
  );
}
