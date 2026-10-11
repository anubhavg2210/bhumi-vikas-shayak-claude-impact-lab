import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as chatApi from '../services/chatApi';

describe('Bhumi Vikas Sahayak App Integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders dashboard with civic branding and example prompt cards', () => {
    render(<App />);

    // Brand headline
    expect(screen.getByText(/Bhumi Vikas Sahayak/i)).toBeDefined();
    expect(screen.getByText(/भूमि विकास सहायक/i)).toBeDefined();

    // Regulatory coverage notice
    expect(screen.getByText(/Statutory Coverage & Legal Scope/i)).toBeDefined();

    // Example categories
    expect(screen.getByText(/Setbacks & Margins/i)).toBeDefined();
    expect(screen.getByText(/FAR & Density/i)).toBeDefined();
  });

  it('switches language between English and Hindi', () => {
    render(<App />);

    const langBtn = screen.getByLabelText(/Change language to Hindi or English/i);
    expect(langBtn.textContent).toContain('हिन्दी');

    // Click to toggle to Hindi
    fireEvent.click(langBtn);

    // In Hindi, button now offers 'English'
    expect(langBtn.textContent).toContain('English');
    expect(screen.getByText(/वैधानिक दायरा एवं कानूनी विस्तार/i)).toBeDefined();
  });

  it('submits an example prompt, transitions to chat, and displays citations', async () => {
    vi.spyOn(chatApi, 'sendChatQuery').mockResolvedValue({
      answer: 'Under Rule 52 of MP Bhumi Vikas Niyam, 2012, setbacks are 3.0m front and 2.4m rear.',
      language: 'en',
      citations: [
        {
          document_title: 'Madhya Pradesh Bhumi Vikas Niyam, 2012',
          rule_number: 'Rule 52, Table No. 13',
          page_number: 48,
          excerpt: 'Minimum front open space shall be 3.0 metres.',
          source_url: 'https://tcpm.mp.gov.in/rules.pdf'
        }
      ],
      confidence: 'high',
      insufficient_evidence: false,
      document_coverage_date: '2025-03-06',
      isMockFallback: true
    });

    render(<App />);

    // Click the first example prompt
    const exampleBtn = screen.getAllByRole('button', { name: /What are the minimum front and rear setback/i })[0];
    fireEvent.click(exampleBtn);

    // Expect loading step
    await waitFor(() => {
      expect(screen.getByText(/Under Rule 52 of MP Bhumi Vikas Niyam/i)).toBeDefined();
    });

    // Check Citation Card
    expect(screen.getByText(/Rule 52, Table No. 13/i)).toBeDefined();
    expect(screen.getByText(/Page 48/i)).toBeDefined();
    expect(screen.getByText(/Minimum front open space shall be 3.0 metres/i)).toBeDefined();
  });

  it('handles insufficient evidence response correctly without citations', async () => {
    vi.spyOn(chatApi, 'sendChatQuery').mockResolvedValue({
      answer: 'The regulatory repository does not contain sufficient statutory text.',
      language: 'en',
      citations: [],
      confidence: 'insufficient',
      insufficient_evidence: true,
      document_coverage_date: '2025-03-06'
    });

    render(<App />);

    const textarea = screen.getByPlaceholderText(/Ask about setbacks, FAR, parking norms/i);
    fireEvent.change(textarea, { target: { value: 'What is the cryptocurrency farming rate?' } });

    const submitBtn = screen.getByRole('button', { name: /Consult Regulations/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Statutory Evidence Not Found in Regulatory Repository/i)).toBeDefined();
    });

    // Verify recommendations are presented
    expect(screen.getByText(/Directorate of Town & Country Planning/i)).toBeDefined();
  });
});
