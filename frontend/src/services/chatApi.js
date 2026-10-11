import { getMockResponse } from './mockData';

// Get base URL from environment; remove trailing slash if present
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const FORCE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// Request timeout in ms. The backend may spend up to LLM_TIMEOUT_SECONDS per LLM attempt
// (plus retries) before answering, so keep this above that. Override with VITE_API_TIMEOUT_MS.
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 90000;
// Document analysis may OCR several pages before answering.
const DOCUMENT_TIMEOUT_MS = Number(import.meta.env.VITE_DOCUMENT_TIMEOUT_MS) || 180000;

// Upload limits mirror the backend defaults (GET /api/documents/limits is authoritative).
export const ACCEPTED_UPLOAD_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.txt'];
export const MAX_UPLOAD_BYTES = Number(import.meta.env.VITE_MAX_UPLOAD_BYTES) || 10 * 1024 * 1024;

function apiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

/** Human-readable message from a FastAPI error body ({message, detail}). */
function describeBackendError(status, bodyText) {
  try {
    const body = JSON.parse(bodyText);
    const details = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg).filter(Boolean).join('; ')
      : typeof body.detail === 'string' ? body.detail : '';
    const summary = [body.message, details].filter(Boolean).join(' ');
    if (summary) return `Backend request failed with status ${status}: ${summary}`;
  } catch {
    // not JSON; fall through
  }
  return `Backend request failed with status ${status}`;
}

/**
 * fetch() with a timeout and consistent errors:
 * - HTTP errors -> Error with `status` and a readable message
 * - timeouts -> Error with `isTimeout`
 * - network failures (backend down, CORS) -> the original error with `isNetwork`
 * Network failures are never answered with mock data: the mock texts are demo content,
 * not verified rules, and would look like a real answer. Mock mode is opt-in only.
 */
async function fetchJson(endpoint, init, timeout) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(endpoint, { ...init, signal: controller.signal });
    clearTimeout(timeoutId);
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      const httpError = new Error(describeBackendError(response.status, errorText));
      httpError.status = response.status;
      throw httpError;
    }
    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      const timeoutError = new Error('Request timed out while consulting regulatory backend.');
      timeoutError.isTimeout = true;
      throw timeoutError;
    }
    const isNetworkError =
      error.message.includes('Failed to fetch') ||
      error.message.includes('NetworkError') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('cross-origin');
    if (isNetworkError) {
      console.warn(`[Bhumi Vikas Sahayak] Backend unreachable at ${endpoint}.`);
      error.isNetwork = true;
    }
    throw error;
  }
}

/** Normalise a backend chat-shaped response (shared by chat and document analysis). */
function normaliseAnswer(data, language) {
  return {
    answer: data.answer || '',
    language: data.language || language,
    citations: Array.isArray(data.citations) ? data.citations : [],
    confidence: data.confidence || (data.insufficient_evidence ? 'insufficient' : 'medium'),
    insufficient_evidence: Boolean(data.insufficient_evidence),
    document_coverage_date: data.document_coverage_date || '2025-03-06',
    isMockFallback: false
  };
}

/**
 * Send inquiry to the MP Bhumi Vikas regulatory RAG backend
 *
 * @param {Object} params
 * @param {string} params.question - The citizen or planner query
 * @param {string} params.language - 'en' or 'hi'
 * @param {boolean} [params.useMock=false] - Explicit override to use mock data
 * @param {number} [params.timeout] - Request timeout in ms
 * @returns {Promise<{
 *   answer: string,
 *   language: string,
 *   citations: Array<{ document_title: string, rule_number: string|null, page_number: number|null, excerpt: string, source_url?: string }>,
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

  // Same-origin '/api/chat' goes through the Vite dev proxy (see vite.config.js)
  const data = await fetchJson(apiUrl('/api/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      question: question.trim(),
      language: language.toLowerCase() === 'hi' ? 'hi' : 'en'
    })
  }, timeout);
  return normaliseAnswer(data, language);
}

/** Client-side check before uploading. Returns an error key for translations, or null. */
export function checkUploadFile(file) {
  if (!file) return 'uploadMissing';
  const name = (file.name || '').toLowerCase();
  if (!ACCEPTED_UPLOAD_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'uploadBadType';
  if (file.size > MAX_UPLOAD_BYTES) return 'uploadTooLarge';
  if (file.size === 0) return 'uploadEmpty';
  return null;
}

/**
 * Upload a document (PDF, image, text) and ask about it.
 * The backend reads it in memory (OCR for scans/photos) and answers against the rules.
 * Returns the chat-shaped answer plus `document` (what was read) and `document_quotes`.
 */
export async function analyzeDocument({ file, question = '', language = 'en', timeout = DOCUMENT_TIMEOUT_MS }) {
  const problem = checkUploadFile(file);
  if (problem) {
    const err = new Error(problem);
    err.uploadErrorKey = problem;
    throw err;
  }
  const form = new FormData();
  form.append('file', file, file.name);
  if (question && question.trim()) form.append('question', question.trim());
  form.append('language', language.toLowerCase() === 'hi' ? 'hi' : 'en');

  // No Content-Type header: the browser sets the multipart boundary.
  const data = await fetchJson(apiUrl('/api/documents/analyze'), {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
    body: form
  }, timeout);
  return {
    ...normaliseAnswer(data, language),
    document: data.document || null,
    document_quotes: Array.isArray(data.document_quotes) ? data.document_quotes : []
  };
}

/**
 * Quick health check to test backend reachability
 * @returns {Promise<boolean>}
 */
export async function checkBackendHealth() {
  // Backend exposes GET /health (not /api/health)
  const endpoint = apiUrl('/health');
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
