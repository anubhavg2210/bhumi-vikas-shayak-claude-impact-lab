import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import { analyzeDocument, checkUploadFile, MAX_UPLOAD_BYTES } from '../services/chatApi';

// Shape returned by POST /api/documents/analyze
const analysisResponse = {
  answer: 'Your document states "Width of road in front of plot: 9 m". Rule 56 says "Up to 9.0 meters 3.0 meters".',
  language: 'en',
  citations: [{
    document_title: 'Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)',
    rule_number: '56', page_number: 77, excerpt: 'Up to 9.0 meters 3.0 meters'
  }],
  confidence: 'high',
  insufficient_evidence: false,
  document_coverage_date: '2025-03-06',
  document: {
    filename: 'plan.pdf', media_type: 'application/pdf', pages_total: 2, pages_read: 2, characters: 300,
    extraction_methods: ['ocr'], ocr_engine: 'cerebras-vision', ocr_is_generative: true, truncated: false,
    warnings: ['Page 2 could not be read by OCR (rate_limited).']
  },
  document_quotes: [{ page: 1, quote: 'Width of road in front of plot: 9 m' }]
};

const pdfFile = (name = 'plan.pdf', size = 1000) => new File([new Uint8Array(size)], name, { type: 'application/pdf' });

function jsonResponse(body, status = 200) {
  return { ok: status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

describe('Document upload', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('validates files before upload', () => {
    expect(checkUploadFile(pdfFile())).toBeNull();
    expect(checkUploadFile(new File(['x'], 'scan.JPG'))).toBeNull();
    expect(checkUploadFile(new File(['x'], 'tool.exe'))).toBe('uploadBadType');
    expect(checkUploadFile(pdfFile('big.pdf', MAX_UPLOAD_BYTES + 1))).toBe('uploadTooLarge');
    expect(checkUploadFile(pdfFile('empty.pdf', 0))).toBe('uploadEmpty');
  });

  it('posts multipart form data to /api/documents/analyze', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(analysisResponse));
    const res = await analyzeDocument({ file: pdfFile(), question: ' Is the front open space enough? ', language: 'hi' });

    const [url, init] = globalThis.fetch.mock.calls[0];
    expect(url).toBe('/api/documents/analyze');
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.get('file').name).toBe('plan.pdf');
    expect(init.body.get('question')).toBe('Is the front open space enough?');
    expect(init.body.get('language')).toBe('hi');
    expect(init.headers['Content-Type']).toBeUndefined(); // browser sets the multipart boundary
    expect(res.document.filename).toBe('plan.pdf');
    expect(res.document_quotes).toHaveLength(1);
  });

  it('surfaces backend upload errors (e.g. 415) readably', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(
      { detail: 'Unsupported file type. Upload a PDF, PNG, JPEG, WebP image, or plain-text file.' }, 415));
    await expect(analyzeDocument({ file: pdfFile() })).rejects.toMatchObject({
      status: 415, message: expect.stringContaining('Unsupported file type')
    });
  });

  it('attaches a document, analyzes it, and shows what was read', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(analysisResponse));
    render(<App />);

    fireEvent.change(screen.getByTestId('document-file-input'), { target: { files: [pdfFile()] } });
    expect(screen.getByText('plan.pdf')).toBeDefined();
    expect(screen.getByText(/read in memory and not stored/i)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: /Consult Regulations/i })); // no question needed

    await waitFor(() => expect(screen.getByTestId('document-read-summary')).toBeDefined());
    expect(screen.getByText('2 of 2 page(s) read')).toBeDefined();
    expect(screen.getByText(/Read by AI-based OCR/)).toBeDefined();
    expect(screen.getByText(/Page 2 could not be read by OCR/)).toBeDefined();
    expect(screen.getByText('“Width of road in front of plot: 9 m”')).toBeDefined();
    expect(screen.getByText('Rule 56')).toBeDefined();
    expect(screen.getByText(/Attached: plan.pdf/)).toBeDefined();
    expect(globalThis.fetch.mock.calls[0][0]).toBe('/api/documents/analyze');
  });

  it('rejects unsupported files in the picker without uploading', () => {
    globalThis.fetch = vi.fn();
    render(<App />);
    fireEvent.change(screen.getByTestId('document-file-input'), { target: { files: [new File(['x'], 'tool.exe')] } });
    expect(screen.getByRole('alert').textContent).toMatch(/Unsupported file type/);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('explains that document analysis needs the Live API in mock mode', async () => {
    localStorage.setItem('bvs_use_mock', 'true');
    globalThis.fetch = vi.fn();
    render(<App />);
    fireEvent.change(screen.getByTestId('document-file-input'), { target: { files: [pdfFile()] } });
    fireEvent.click(screen.getByRole('button', { name: /Consult Regulations/i }));
    await waitFor(() => expect(screen.getByText(/Document analysis needs the Live API/)).toBeDefined());
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
