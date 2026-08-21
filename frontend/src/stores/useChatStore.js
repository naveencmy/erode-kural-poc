import { create } from 'zustand';

const useChatStore = create((set, get) => ({
  // ─── Speech-to-Text State ──────────────
  isListening: false,
  speechLang: localStorage.getItem('tn-speech-lang') || 'ta-IN', // 'ta-IN' or 'en-IN'
  draftText: '',
  recognition: null,
  speakingMessageId: null,

  setSpeechLang: (lang) => {
    localStorage.setItem('tn-speech-lang', lang);
    set({ speechLang: lang });
  },

  setDraftText: (text) => set({ draftText: text }),

  // ─── Speech-to-Text Streaming (Speed-to-Typing) ────
  startListening: (onInterimResult, onAutoSubmit) => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('உங்கள் உலாவியில் குரல் அறிதல் ஆதரிக்கப்படவில்லை. Chrome/Edge உலாவியைப் பயன்படுத்தவும்.');
      return;
    }

    // Stop existing recognition if running
    if (get().recognition) {
      try {
        get().recognition.stop();
      } catch (e) {}
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true; // Real-time high-speed streaming typing
      recognition.lang = get().speechLang;

      recognition.onstart = () => {
        set({ isListening: true });
      };

      recognition.onresult = (event) => {
        let transcriptStr = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcriptStr += event.results[i][0].transcript;
        }
        if (transcriptStr) {
          set({ draftText: transcriptStr });
          if (onInterimResult) {
            onInterimResult(transcriptStr);
          }
        }
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        set({ isListening: false, recognition: null });
      };

      recognition.onend = () => {
        set({ isListening: false, recognition: null });
        const finalContent = get().draftText;
        if (onAutoSubmit && finalContent && finalContent.trim()) {
          onAutoSubmit(finalContent.trim());
        }
      };

      recognition.start();
      set({ recognition });
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      set({ isListening: false, recognition: null });
    }
  },

  stopListening: () => {
    const rec = get().recognition;
    if (rec) {
      try {
        rec.stop();
      } catch (e) {}
    }
    set({ isListening: false, recognition: null });
  },

  // ─── Text-to-Speech (TTS) Voice Response ───────
  speakText: (msgId, rawText) => {
    if (!('speechSynthesis' in window)) {
      alert('உங்கள் உலாவியில் குரல் வாசிப்பு வசதி இல்லை.');
      return;
    }

    // If already speaking this message, cancel and stop
    if (get().speakingMessageId === msgId) {
      window.speechSynthesis.cancel();
      set({ speakingMessageId: null });
      return;
    }

    window.speechSynthesis.cancel();

    // Strip Markdown symbols for clean speech synthesis
    const cleanText = rawText
      .replace(/[*_#`~[\]()]/g, '')
      .replace(/•/g, ' ')
      .replace(/📌|📂|🏛️|⚡|📄/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = get().speechLang;
    utterance.rate = 0.95; // Natural speaking rate for Tamil

    utterance.onstart = () => set({ speakingMessageId: msgId });
    utterance.onend = () => set({ speakingMessageId: null });
    utterance.onerror = () => set({ speakingMessageId: null });

    window.speechSynthesis.speak(utterance);
  },

  stopSpeech: () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    set({ speakingMessageId: null });
  },
}));

export default useChatStore;
