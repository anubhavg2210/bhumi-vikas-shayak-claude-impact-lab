import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import RegulatoryNoticeBanner from './components/RegulatoryNoticeBanner';
import DashboardHero from './components/DashboardHero';
import ExamplePrompts from './components/ExamplePrompts';
import ChatContainer from './components/ChatContainer';
import ChatInput from './components/ChatInput';
import CitationViewerModal from './components/CitationViewerModal';
import { sendChatQuery, analyzeDocument } from './services/chatApi';
import { translations } from './i18n/translations';
import { speak, stopSpeaking, isSpeechSynthesisSupported } from './services/speech';
import './App.css';

export default function App() {
  // 1. Language state: English or Hindi
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('bvs_language') || 'en';
  });

  // 2. Chat history messages state
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem('bvs_messages');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // 3. Loading & error states
  const [isLoading, setIsLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  // File objects are kept in memory only (not persisted) so a failed upload can be retried.
  const [lastFile, setLastFile] = useState(null);

  // 4. Mock mode toggle: whether to force offline mock data or call real backend
  const [isMockMode, setIsMockMode] = useState(() => {
    const envMock = import.meta.env.VITE_USE_MOCK === 'true';
    const stored = localStorage.getItem('bvs_use_mock');
    return stored !== null ? stored === 'true' : envMock;
  });

  // 5. Active citation for the modal viewer
  const [selectedCitation, setSelectedCitation] = useState(null);

  // 6. Colour theme: saved choice, else the OS preference
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem('bvs_theme');
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // 7. Spoken answers: mute preference and the timestamp of the answer being read aloud
  const canSpeak = isSpeechSynthesisSupported();
  const [isMuted, setIsMuted] = useState(() => localStorage.getItem('bvs_muted') === 'true');
  const [speakingKey, setSpeakingKey] = useState(null);
  // Read inside the async send handler, where the mute state may change mid-request.
  const isMutedRef = useRef(isMuted);

  // Sync language to local storage
  useEffect(() => {
    localStorage.setItem('bvs_language', language);
    document.documentElement.lang = language;
  }, [language]);

  // Apply theme to the document
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('bvs_theme', theme);
  }, [theme]);

  // Stop reading aloud when the language changes or the app unmounts
  useEffect(() => stopSpeaking, [language]);

  // Sync messages to session storage
  useEffect(() => {
    try {
      sessionStorage.setItem('bvs_messages', JSON.stringify(messages));
    } catch (e) {
      console.warn('Could not persist messages to sessionStorage', e);
    }
  }, [messages]);

  // Sync mock mode preference
  const handleToggleMockMode = useCallback(() => {
    setIsMockMode((prev) => {
      const next = !prev;
      localStorage.setItem('bvs_use_mock', String(next));
      return next;
    });
  }, []);

  const handleToggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const handleToggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      localStorage.setItem('bvs_muted', String(next));
      isMutedRef.current = next;
      if (next) stopSpeaking();
      return next;
    });
  }, []);

  const speakMessage = useCallback((message) => {
    const started = speak(message.content, message.language || language, {
      onEnd: () => setSpeakingKey((key) => (key === message.timestamp ? null : key))
    });
    setSpeakingKey(started ? message.timestamp : null);
  }, [language]);

  // Listen / Stop button on an answer
  const handleToggleSpeak = useCallback((message) => {
    if (speakingKey === message.timestamp) {
      stopSpeaking();
    } else {
      speakMessage(message);
    }
  }, [speakingKey, speakMessage]);

  // Handle submitting a question (either from hero input, example cards, or chat input).
  // Every answer is read aloud unless muted.
  const handleSendMessage = useCallback(
    async (questionText, file = null) => {
      const text = (questionText || '').trim();
      if ((!text && !file) || isLoading) return;

      const userMessage = {
        role: 'user',
        content: text,
        attachment: file ? { name: file.name, size: file.size } : null,
        timestamp: new Date().toISOString()
      };

      stopSpeaking();
      setMessages((prev) => [...prev, userMessage]);
      setLastQuery(text);
      setLastFile(file);
      setIsLoading(true);

      let replyMessage;
      try {
        if (file && isMockMode) {
          throw new Error(translations[language].documentNeedsLive);
        }
        const response = file
          ? await analyzeDocument({ file, question: text, language })
          : await sendChatQuery({ question: text, language, useMock: isMockMode });

        const assistantMessage = {
          role: 'assistant',
          content: response.answer,
          language: response.language || language,
          citations: response.citations || [],
          confidence: response.confidence || 'medium',
          insufficient_evidence: Boolean(response.insufficient_evidence),
          document_coverage_date: response.document_coverage_date || '2025-03-06',
          isMockFallback: Boolean(response.isMockFallback),
          document: response.document || null,
          document_quotes: response.document_quotes || [],
          timestamp: new Date().toISOString()
        };

        replyMessage = assistantMessage;
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Error during chat query:', error);
        const t = translations[language];
        let errorMessageText = t.errorGenericTitle;

        if (error.uploadErrorKey) {
          errorMessageText = t[error.uploadErrorKey];
        } else if (error.isTimeout) {
          errorMessageText = t.errorTimeout;
        } else if (error.isNetwork || error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          errorMessageText = t.errorNetwork;
        } else {
          errorMessageText = `${t.errorGenericTitle}: ${error.message}`;
        }

        const errorMessage = {
          role: 'assistant',
          content: errorMessageText,
          language,
          isError: true,
          timestamp: new Date().toISOString()
        };

        replyMessage = errorMessage;
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }

      if (!isMutedRef.current) {
        speakMessage(replyMessage);
      }
    },
    [isLoading, language, isMockMode, speakMessage]
  );

  // Retry query handler
  const handleRetry = useCallback(
    (messageIndex) => {
      if (lastQuery || lastFile) {
        // Remove error message if requested
        if (messageIndex !== undefined) {
          setMessages((prev) => prev.filter((_, idx) => idx !== messageIndex));
        }
        handleSendMessage(lastQuery, lastFile);
      }
    },
    [lastQuery, lastFile, handleSendMessage]
  );

  // Clear session to return to fresh Dashboard
  const handleClearSession = useCallback(() => {
    stopSpeaking();
    setMessages([]);
    setLastQuery('');
    setLastFile(null);
    sessionStorage.removeItem('bvs_messages');
  }, []);

  return (
    <div className="app-wrapper">
      {/* Header with civic branding, language selector, mock toggle */}
      <Header
        language={language}
        onLanguageChange={setLanguage}
        onClearSession={handleClearSession}
        isMockMode={isMockMode}
        onToggleMockMode={handleToggleMockMode}
        hasMessages={messages.length > 0}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        canSpeak={canSpeak}
        isMuted={isMuted}
        onToggleMute={handleToggleMute}
      />

      {/* Statutory Coverage Notice Banner */}
      <RegulatoryNoticeBanner language={language} />

      {/* Main Content Area */}
      <main className="main-content" id="main-content">
        {messages.length === 0 ? (
          // Dashboard View: Hero with Main Input, Regulatory Stats, Example Prompts
          <>
            <DashboardHero
              language={language}
              onSubmitQuery={handleSendMessage}
              isLoading={isLoading}
            />
            <ExamplePrompts
              language={language}
              onSelectExample={handleSendMessage}
              isLoading={isLoading}
            />
          </>
        ) : (
          // Active Consultation Chat View
          <>
            <ChatContainer
              messages={messages}
              isLoading={isLoading}
              language={language}
              onInspectCitation={setSelectedCitation}
              onRetry={handleRetry}
              canSpeak={canSpeak && !isMuted}
              speakingKey={speakingKey}
              onToggleSpeak={handleToggleSpeak}
            />
            <ChatInput
              language={language}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
            />
          </>
        )}
      </main>

      {/* Citation Inspector Modal */}
      {selectedCitation && (
        <CitationViewerModal
          citation={selectedCitation}
          language={language}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
}
