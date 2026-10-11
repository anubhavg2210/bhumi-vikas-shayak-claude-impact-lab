import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import App from '../App';
import * as chatApi from '../services/chatApi';
import { textForSpeech } from '../services/speech';

let recognitions;

class FakeRecognition {
  constructor() {
    this.start = vi.fn();
    this.stop = vi.fn(() => this.onend && this.onend());
    this.abort = vi.fn();
    recognitions.push(this);
  }
}

class FakeUtterance {
  constructor(text) {
    this.text = text;
  }
}

function say(recognition, transcript) {
  const result = Object.assign([{ transcript }], { isFinal: true });
  act(() => {
    recognition.onresult({ resultIndex: 0, results: [result] });
    recognition.onend();
  });
}

function mockAnswer(answer, language = 'en') {
  return vi.spyOn(chatApi, 'sendChatQuery').mockResolvedValue({
    answer,
    language,
    citations: [],
    confidence: 'high',
    insufficient_evidence: false,
    document_coverage_date: '2025-03-06'
  });
}

describe('Voice questions, spoken answers, mute and dark mode', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
    recognitions = [];
    window.SpeechRecognition = FakeRecognition;
    window.SpeechSynthesisUtterance = FakeUtterance;
    window.speechSynthesis = { speak: vi.fn(), cancel: vi.fn(), resume: vi.fn(), getVoices: () => [] };
  });

  afterEach(() => {
    delete window.SpeechRecognition;
    delete window.SpeechSynthesisUtterance;
    delete window.speechSynthesis;
    delete document.documentElement.dataset.theme;
  });

  it('asks a spoken English question and reads the answer aloud in English', async () => {
    const spy = mockAnswer('Front setback is **3.0 m** under Rule 52.');
    render(<App />);

    fireEvent.click(screen.getByLabelText('Speak'));
    expect(recognitions).toHaveLength(1);
    expect(recognitions[0].lang).toBe('en-IN');
    expect(recognitions[0].start).toHaveBeenCalled();

    say(recognitions[0], 'What is the front setback?');

    await waitFor(() => expect(window.speechSynthesis.speak).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ question: 'What is the front setback?', language: 'en' }));
    const utterance = window.speechSynthesis.speak.mock.calls[0][0];
    expect(utterance.lang).toBe('en-IN');
    expect(utterance.text).toBe('Front setback is 3.0 m under Rule 52.');
  });

  it('listens and speaks in Hindi when the interface is in Hindi', async () => {
    const spy = mockAnswer('नियम 52 के अनुसार अग्र सेटबैक 3.0 मीटर है।', 'hi');
    render(<App />);
    fireEvent.click(screen.getByLabelText(/Change language to Hindi or English/i));

    fireEvent.click(screen.getByLabelText('बोलें'));
    expect(recognitions[0].lang).toBe('hi-IN');

    say(recognitions[0], 'अग्र सेटबैक कितना है');

    await waitFor(() => expect(window.speechSynthesis.speak).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ question: 'अग्र सेटबैक कितना है', language: 'hi' }));
    expect(window.speechSynthesis.speak.mock.calls[0][0].lang).toBe('hi-IN');
  });

  it('does not speak the answer when muted, and remembers the choice', async () => {
    const spy = mockAnswer('Answer text.');
    render(<App />);

    fireEvent.click(screen.getByLabelText('Mute spoken answers'));
    expect(localStorage.getItem('bvs_muted')).toBe('true');
    expect(screen.getByLabelText('Unmute spoken answers')).toBeDefined();

    fireEvent.click(screen.getByLabelText('Speak'));
    say(recognitions[0], 'A question');

    await waitFor(() => expect(spy).toHaveBeenCalled());
    await screen.findByText('Answer text.');
    expect(window.speechSynthesis.speak).not.toHaveBeenCalled();
    expect(screen.queryByLabelText('Listen')).toBeNull();
  });

  it('reads typed answers aloud too, with a Listen / Stop toggle', async () => {
    mockAnswer('Typed answer.');
    render(<App />);

    const input = screen.getByLabelText(/Ask about MP building regulations/i);
    fireEvent.change(input, { target: { value: 'Typed question' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await screen.findByText('Typed answer.');
    await waitFor(() => expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1));
    expect(screen.getByLabelText('Stop')).toBeDefined();

    fireEvent.click(screen.getByLabelText('Stop'));
    expect(screen.getByLabelText('Listen')).toBeDefined();

    fireEvent.click(screen.getByLabelText('Listen'));
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(2);
  });

  it('speaks a long answer one sentence at a time', async () => {
    mockAnswer('First sentence. Second sentence.');
    render(<App />);
    fireEvent.click(screen.getByLabelText('Speak'));
    say(recognitions[0], 'A question');

    await waitFor(() => expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1));
    const first = window.speechSynthesis.speak.mock.calls[0][0];
    expect(first.text).toBe('First sentence.');
    act(() => first.onend());
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(2);
    expect(window.speechSynthesis.speak.mock.calls[1][0].text).toBe('Second sentence.');
  });

  it('tells the user when listening ends without recognising any words', () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText('Speak'));
    act(() => recognitions[0].onend());
    expect(screen.getByRole('alert').textContent).toMatch(/No words were recognised/);
  });

  it('uses the interim transcript when recognition ends without a final result', async () => {
    const spy = mockAnswer('Answer.');
    render(<App />);
    fireEvent.click(screen.getByLabelText('Speak'));
    const interim = Object.assign([{ transcript: 'parking rules' }], { isFinal: false });
    act(() => {
      recognitions[0].onresult({ resultIndex: 0, results: [interim] });
      recognitions[0].onend();
    });
    await waitFor(() => expect(spy).toHaveBeenCalledWith(expect.objectContaining({ question: 'parking rules' })));
  });

  it('toggles dark mode and persists it', () => {
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe('light');

    fireEvent.click(screen.getByLabelText('Switch to dark mode'));
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(localStorage.getItem('bvs_theme')).toBe('dark');

    fireEvent.click(screen.getByLabelText('Switch to light mode'));
    expect(document.documentElement.dataset.theme).toBe('light');
  });

  it('hides the voice and mute controls when the browser has no speech support', () => {
    delete window.SpeechRecognition;
    delete window.speechSynthesis;
    render(<App />);
    expect(screen.queryByLabelText('Speak')).toBeNull();
    expect(screen.queryByLabelText('Mute spoken answers')).toBeNull();
  });
});

describe('textForSpeech', () => {
  it('strips markdown bullets and bold markers', () => {
    expect(textForSpeech('**Rule 52**: setbacks\n\n* Front: 3 m\n* Rear: 2.4 m')).toBe('Rule 52: setbacks. Front: 3 m. Rear: 2.4 m');
  });
});
