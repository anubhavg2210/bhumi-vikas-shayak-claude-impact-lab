import { getMockResponse } from './mockData';

// Get base URL from environment; remove trailing slash if present
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const FORCE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// Configurable request timeout in ms
const DEFAULT_TIMEOUT_MS = 25000;

/**
 * Send inquiry to the MP Bhumi Vikas regulatory RAG backend
 * 
 * @param {Object} params
 * @param {string} params.question - The citizen or planner query
 * @param {string} params.language - 'en' or 'hi'
 * @param {boolean} [params.useMock=false] - Explicit override to use mock data
 * @param {number} [params.timeout=25000] - Request timeout in ms
 * @returns {Promise<{
 *   answer: string,
 *   language: string,
 *   citations: Array<{ document_title: string, rule_number: string, page_number: number, excerpt: string, source_url?: string }>,
 *   confidence: 'high' | 'medium' | 'low' | 'insufficient',
 *   insufficient_evidence: boolean,
 *   document_coverage_date: string,
 *   isMockFallback?: boolean
 * }>}
 */
export async function sendChatQuery({ question, language = 'en', useMock = false, timeout = DEFAULT_TIMEOUT_MS }) {
  if (!question || !question.trim()) {
    throw new Error('Question must not be empty.');
  }

  // If user requested mock or environment variable explicitly enables it
  if (FORCE_MOCK || useMock) {
    // Simulate slight natural latency for realistic UX feel
    await new Promise((resolve) => setTimeout(resolve, 850));
    const mockData = getMockResponse(question, language);
    return {
      ...mockData,
      isMockFallback: true
    };
  }

  // Construct target endpoint
  const endpoint = API_BASE_URL ? `${API_BASE_URL}/api/chat` : '/api/chat';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        question: question.trim(),
        language: language.toLowerCase() === 'hi' ? 'hi' : 'en'
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      throw new Error(
        `Backend request failed with status ${response.status}${errorText ? `: ${errorText}` : ''}`
      );
    }

    const data = await response.json();

    // Validate expected structure and provide safe fallbacks
    return {
      answer: data.answer || '',
      language: data.language || language,
      citations: Array.isArray(data.citations) ? data.citations : [],
      confidence: data.confidence || (data.insufficient_evidence ? 'insufficient' : 'medium'),
      insufficient_evidence: Boolean(data.insufficient_evidence),
      document_coverage_date: data.document_coverage_date || '2025-03-06',
      isMockFallback: false
    };
  } catch (error) {
    clearTimeout(timeoutId);

    // If abort / timeout error
    if (error.name === 'AbortError') {
      const timeoutError = new Error('Request timed out while consulting regulatory backend.');
      timeoutError.isTimeout = true;
      throw timeoutError;
    }

    // For network failure during parallel development (backend not running yet):
    // Check if error is network connection failure
    const isNetworkError =
      error.message.includes('Failed to fetch') ||
      error.message.includes('NetworkError') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('cross-origin');

    if (isNetworkError) {
      console.warn(
        `[Bhumi Vikas Sahayak] Backend unreachable at ${endpoint}. Seamlessly falling back to realistic mock regulatory data for parallel development.`
      );
      // Gracefully fall back to verified mock data with isMockFallback flag
      const mockData = getMockResponse(question, language);
      return {
        ...mockData,
        isMockFallback: true
      };
    }

    // Otherwise re-throw error for UI error handling
    throw error;
  }
}

/**
 * Quick health check to test backend reachability
 * @returns {Promise<boolean>}
 */
export async function checkBackendHealth() {
  const endpoint = API_BASE_URL ? `${API_BASE_URL}/api/health` : '/api/health';
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(endpoint, { method: 'GET', signal: controller.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}
