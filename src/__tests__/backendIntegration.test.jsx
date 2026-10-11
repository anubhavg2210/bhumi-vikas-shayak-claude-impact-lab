import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import ChatMessage from '../components/ChatMessage';
import { sendChatQuery, checkBackendHealth } from '../services/chatApi';
import { formatRuleLabel } from '../services/citationFormat';

// A response exactly as the FastAPI backend returns it (see backend/API_CONTRACT.md):
// rule_number is the bare printed number, page_number may be null, no source_url.
const backendResponse = {
  answer: 'Rule 56 says "Above 40.00 and up to 150.00 1.50".\n\nNote: this answer is based on the rules as consolidated up to 2025-03-06.',
  language: 'en',
  citations: [
    {
      document_title: 'Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)',
      rule_number: '56',
      page_number: 78,
      excerpt: 'Above 40.00 and up to 150.00 1.50'
    },
    {
      document_title: 'Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)',
      rule_number: null,
      page_number: null,
      excerpt: 'A passage whose rule and page could not be confirmed.'
    }
  ],
  confidence: 'high',
  insufficient_evidence: false,
  document_coverage_date: '2025-03-06'
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body)
  };
}

describe('Backend integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('posts to the same-origin /api/chat (proxied in dev) with the contract body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(backendResponse));
    const res = await sendChatQuery({ question: '  rear open space 150 sq m  ', language: 'hi' });

    const [url, init] = globalThis.fetch.mock.calls[0];
    expect(url).toBe('/api/chat');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ question: 'rear open space 150 sq m', language: 'hi' });
    expect(res.citations).toHaveLength(2);
    expect(res.isMockFallback).toBe(false);
  });

  it('turns FastAPI 422 bodies into a readable message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({
      detail: [{ type: 'value_error', loc: ['body', 'language'], msg: "Value error, Unsupported language. Use 'en' or 'hi'." }],
      message: 'Invalid request parameters.'
    }, 422));

    await expect(sendChatQuery({ question: 'x', language: 'en' })).rejects.toMatchObject({
      status: 422,
      message: expect.stringContaining('Invalid request parameters. Value error, Unsupported language')
    });
  });

  it('health check uses the backend /health route', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ status: 'healthy' }));
    expect(await checkBackendHealth()).toBe(true);
    expect(globalThis.fetch.mock.calls[0][0]).toBe('/health');
  });

  it('formats backend rule numbers for display', () => {
    expect(formatRuleLabel('56', 'en')).toBe('Rule 56');
    expect(formatRuleLabel('26-B', 'hi')).toBe('नियम 26-B');
    expect(formatRuleLabel(null, 'en')).toBe('Rule not identified');
    expect(formatRuleLabel('Rule 52, Table No. 13', 'en')).toBe('Rule 52, Table No. 13');
  });

  it('renders a real backend answer with rule labels and handles null rule/page', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(backendResponse));
    render(<App />);

    fireEvent.change(screen.getByPlaceholderText(/Ask about setbacks, FAR, parking norms/i), {
      target: { value: 'What is the minimum rear open space for a 150 sq m residential plot?' }
    });
    fireEvent.click(screen.getByRole('button', { name: /Consult Regulations/i }));

    await waitFor(() => expect(screen.getByText('Rule 56')).toBeDefined());
    expect(screen.getByText(/Page 78/)).toBeDefined();
    expect(screen.getByText('Rule not identified')).toBeDefined();
    expect(screen.getAllByText(/Page/).length).toBe(1); // no page badge for the null page
    expect(screen.getByText(/later amendments|consolidated up to 2025-03-06/)).toBeDefined();
    expect(screen.queryByText(/Demo data \(mock mode\)/)).toBeNull();
  });

  it('shows a network error with retry (no mock answer) when the backend is down', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    render(<App />);

    fireEvent.change(screen.getByPlaceholderText(/Ask about setbacks, FAR, parking norms/i), {
      target: { value: 'What are setback rules?' }
    });
    fireEvent.click(screen.getByRole('button', { name: /Consult Regulations/i }));

    await waitFor(() => expect(screen.getByText(/Could not connect to the regulatory backend/i)).toBeDefined());
    expect(screen.getByRole('button', { name: /Retry Query/i })).toBeDefined();
    expect(screen.queryByText(/Rule 52/)).toBeNull();
  });

  it('labels every mock-mode answer as unverified demo data', () => {
    render(
      <ChatMessage
        language="en"
        onInspectCitation={() => {}}
        message={{ role: 'assistant', content: 'Sample', citations: [], confidence: 'high', isMockFallback: true }}
      />
    );
    expect(screen.getByRole('note').textContent).toMatch(/Demo data \(mock mode\).*not verified/);
  });
});
