/**
 * Browser speech helpers (Web Speech API) for voice questions and spoken answers.
 * Everything degrades to a no-op when the browser lacks support (e.g. Firefox, JSDOM).
 */

// Chrome cuts off long utterances after ~15 s, so answers are spoken in short chunks.
const MAX_CHUNK_CHARS = 180;

export function speechLang(language) {
  return language === 'hi' ? 'hi-IN' : 'en-IN';
}

export function getSpeechRecognition() {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function isSpeechSynthesisSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function';
}

/** Strip the light markdown used in answers so it is not read aloud. */
export function textForSpeech(text) {
  return (text || '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/^\s*[*-]\s+/gm, '')
    .replace(/[*_`#>]/g, '')
    .replace(/\s*\n+\s*/g, '. ')
    .replace(/(\.\s*){2,}/g, '. ')
    .trim();
}

function splitIntoChunks(text) {
  const sentences = text.split(/(?<=[.!?।])\s+/);
  const chunks = [];
  for (const sentence of sentences) {
    let rest = sentence.trim();
    while (rest.length > MAX_CHUNK_CHARS) {
      // Break at the last comma or space before the limit.
      let cut = Math.max(rest.lastIndexOf(',', MAX_CHUNK_CHARS), rest.lastIndexOf(' ', MAX_CHUNK_CHARS));
      if (cut <= 0) cut = MAX_CHUNK_CHARS;
      chunks.push(rest.slice(0, cut + 1).trim());
      rest = rest.slice(cut + 1).trim();
    }
    if (rest) chunks.push(rest);
  }
  return chunks;
}

function pickVoice(lang) {
  const voices = window.speechSynthesis.getVoices() || [];
  const prefix = lang.split('-')[0];
  return (
    voices.find((v) => v.lang === lang) ||
    voices.find((v) => v.lang && v.lang.replace('_', '-').toLowerCase().startsWith(prefix)) ||
    null
  );
}

// Voices load asynchronously in Chrome; touching getVoices() early starts the load.
if (isSpeechSynthesisSupported()) {
  window.speechSynthesis.getVoices();
}

// Completion callback of the text being spoken now. cancel() does not reliably fire
// onend/onerror, so stopping or starting new speech calls it directly.
let finishCurrent = null;
// Bumped on every speak/stop so callbacks from cancelled speech are ignored.
let session = 0;
// Chrome garbage-collects utterances nothing references, and then never fires their events.
// oxlint-disable-next-line no-unused-vars -- held only so the utterance is not garbage-collected
let currentUtterance = null;

/**
 * Speak text in the given language ('en' | 'hi'), replacing anything already being spoken.
 * onEnd fires once when the whole text finishes, fails, or is interrupted by stopSpeaking()/speak().
 */
export function speak(text, language, { onEnd } = {}) {
  if (!isSpeechSynthesisSupported()) return false;
  stopSpeaking();

  const chunks = splitIntoChunks(textForSpeech(text));
  if (chunks.length === 0) return false;

  const synth = window.speechSynthesis;
  const mySession = session;
  const lang = speechLang(language);
  const voice = pickVoice(lang);
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    if (finishCurrent === finish) finishCurrent = null;
    if (onEnd) onEnd();
  };
  finishCurrent = finish;

  // Queue one chunk at a time: Chrome on Windows stalls after the first of several queued utterances.
  let next = 0;
  const speakNext = () => {
    if (mySession !== session || finished) return;
    if (next >= chunks.length) {
      currentUtterance = null;
      finish();
      return;
    }
    const utterance = new window.SpeechSynthesisUtterance(chunks[next++]);
    utterance.lang = lang;
    if (voice) utterance.voice = voice;
    utterance.rate = 0.95;
    utterance.onend = speakNext;
    utterance.onerror = finish;
    currentUtterance = utterance;
    synth.speak(utterance);
  };

  synth.resume(); // Chrome can be left paused, which silently holds the queue
  speakNext();
  return true;
}

export function stopSpeaking() {
  if (!isSpeechSynthesisSupported()) return;
  session++;
  currentUtterance = null;
  window.speechSynthesis.cancel();
  if (finishCurrent) finishCurrent();
}
