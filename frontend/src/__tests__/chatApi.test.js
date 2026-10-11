import { describe, it, expect, vi, beforeEach } from 'vitest';
import { sendChatQuery } from '../services/chatApi';
import { getMockResponse } from '../services/mockData';

describe('chatApi Service & Schema Verification', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('validates empty questions and throws an error', async () => {
    await expect(sendChatQuery({ question: '' })).rejects.toThrow('Question must not be empty.');
    await expect(sendChatQuery({ question: '   ' })).rejects.toThrow('Question must not be empty.');
  });

  it('returns valid mock schema when useMock is true', async () => {
    const res = await sendChatQuery({
      question: 'What are the building setback requirements?',
      language: 'en',
      useMock: true
    });

    expect(res).toBeDefined();
    expect(res.answer).toContain('Rule 52');
    expect(res.language).toBe('en');
    expect(Array.isArray(res.citations)).toBe(true);
    expect(res.citations.length).toBeGreaterThan(0);
    expect(res.citations[0]).toHaveProperty('document_title');
    expect(res.citations[0]).toHaveProperty('rule_number');
    expect(res.citations[0]).toHaveProperty('page_number');
    expect(res.citations[0]).toHaveProperty('excerpt');
    expect(res.confidence).toBe('high');
    expect(res.insufficient_evidence).toBe(false);
    expect(res.document_coverage_date).toBe('2025-03-06');
    expect(res.isMockFallback).toBe(true);
  });

  it('handles Hindi language query correctly', async () => {
    const res = await sendChatQuery({
      question: '250 वर्ग मीटर के आवासीय भूखंड के लिए सेटबैक क्या है?',
      language: 'hi',
      useMock: true
    });

    expect(res.language).toBe('hi');
    expect(res.answer).toContain('नियम 52');
    expect(res.citations[0].rule_number).toContain('नियम 52');
  });

  it('identifies unindexed topics as insufficient evidence', async () => {
    const res = await sendChatQuery({
      question: 'What is the cryptocurrency subsidy for wheat farming in Mars?',
      language: 'en',
      useMock: true
    });

    expect(res.insufficient_evidence).toBe(true);
    expect(res.confidence).toBe('insufficient');
    expect(res.citations).toHaveLength(0);
    expect(res.answer).toContain('does not contain sufficient verified statutory evidence');
  });

  it('surfaces network errors instead of silently answering with mock data', async () => {
    // Backend not running / CORS failure: the UI must show an error, never demo content
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(
      sendChatQuery({ question: 'What are setback rules?', language: 'en', useMock: false })
    ).rejects.toMatchObject({ isNetwork: true });
  });

  it('handles backend response conforming to contract', async () => {
    const backendData = {
      answer: 'Rule 52 states setbacks are 3.0m front and 2.4m rear.',
      language: 'en',
      citations: [
        {
          document_title: 'MP Bhumi Vikas Niyam, 2012',
          rule_number: 'Rule 52',
          page_number: 48,
          excerpt: 'Minimum front setback shall be 3.0 metres.'
        }
      ],
      confidence: 'high',
      insufficient_evidence: false,
      document_coverage_date: '2025-03-06'
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => backendData
    });

    const res = await sendChatQuery({
      question: 'What are setbacks?',
      language: 'en',
      useMock: false
    });

    expect(res.answer).toBe(backendData.answer);
    expect(res.citations).toHaveLength(1);
    expect(res.confidence).toBe('high');
    expect(res.insufficient_evidence).toBe(false);
    expect(res.isMockFallback).toBe(false);
  });
});
