import React, { useEffect, useRef, useState } from 'react';
import { Mic, Square } from 'lucide-react';
import { translations } from '../i18n/translations';
import { getSpeechRecognition, speechLang, stopSpeaking } from '../services/speech';

/**
 * Microphone button: listens in the current UI language (English or Hindi),
 * streams the interim transcript to onInterim and hands the final one to onFinal.
 * Renders nothing in browsers without speech recognition.
 */
const VOICE_ERROR_KEYS = {
  'not-allowed': 'voiceErrorPermission',
  'service-not-allowed': 'voiceErrorPermission',
  'no-speech': 'voiceErrorNoSpeech',
  'audio-capture': 'voiceErrorNoMic',
  network: 'voiceErrorNetwork',
  'language-not-supported': 'voiceErrorLanguage'
};

export default function VoiceInputButton({ language, disabled, onInterim, onFinal, onError }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  // Keep the latest callbacks without restarting recognition when parents re-render.
  const callbacksRef = useRef({ onInterim, onFinal, onError });
  useEffect(() => {
    callbacksRef.current = { onInterim, onFinal, onError };
  });
  const t = translations[language];
  const Recognition = getSpeechRecognition();

  useEffect(() => () => recognitionRef.current && recognitionRef.current.abort(), []);

  if (!Recognition) return null;

  const start = () => {
    stopSpeaking(); // do not transcribe our own spoken answer
    const recognition = new Recognition();
    recognition.lang = speechLang(language);
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    let finalText = '';
    let heardText = ''; // final + interim; Chrome may end (e.g. after Stop) without marking a result final
    let errorShown = false;
    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) finalText += result[0].transcript;
        else interim += result[0].transcript;
      }
      heardText = (finalText + interim).trim();
      callbacksRef.current.onInterim?.(heardText);
    };
    recognition.onerror = (event) => {
      if (event.error === 'aborted') return;
      errorShown = true;
      const key = VOICE_ERROR_KEYS[event.error];
      callbacksRef.current.onError?.(key ? t[key] : `${t.voiceErrorGeneric} (${event.error})`);
    };
    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
      const spoken = finalText.trim() || heardText;
      if (spoken) callbacksRef.current.onFinal?.(spoken);
      // Chrome sometimes hears speech but ends with no words and no error; say so instead of silently resetting.
      else if (!errorShown) callbacksRef.current.onError?.(t.voiceErrorNoSpeech);
    };

    recognitionRef.current = recognition;
    callbacksRef.current.onError?.('');
    try {
      recognition.start();
      setListening(true);
    } catch {
      recognitionRef.current = null;
      callbacksRef.current.onError?.(t.voiceErrorGeneric);
    }
  };

  const stop = () => recognitionRef.current && recognitionRef.current.stop();

  return (
    <button
      type="button"
      className={`btn-outline voice-btn ${listening ? 'is-listening' : ''}`}
      onClick={listening ? stop : start}
      disabled={disabled && !listening}
      title={listening ? t.voiceStop : t.voiceStartHint}
      aria-label={listening ? t.voiceStop : t.voiceStart}
      aria-pressed={listening}
    >
      {listening ? <Square size={13} /> : <Mic size={14} />}
      <span className="voice-btn-label">{listening ? t.voiceListening : t.voiceStart}</span>
    </button>
  );
}
