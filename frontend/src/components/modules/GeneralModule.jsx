import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import useChatStore from '../../stores/useChatStore';
import { sendChat, uploadDocument, trackSuggestionClick } from '../../lib/api';
import TnEmblem from '../icons/TnEmblem';
import {
  Send,
  Bot,
  User,
  Sparkles,
  Paperclip,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  FileText,
  X,
  Languages,
} from 'lucide-react';

// Pastel palette modeled after the reference speech-bubble design
const PASTEL_BUBBLES = [
  {
    bg: '#e8f5e9',
    color: '#1b5e20',
    border: '#a5d6a7',
    shadow: '#81c784',
  },
  {
    bg: '#ffebee',
    color: '#b71c1c',
    border: '#ffcdd2',
    shadow: '#ef9a9a',
  },
  {
    bg: '#e1f5fe',
    color: '#01579b',
    border: '#b3e5fc',
    shadow: '#81d4fa',
  },
  {
    bg: '#fff8e1',
    color: '#e65100',
    border: '#ffe082',
    shadow: '#ffd54f',
  },
  {
    bg: '#f3e5f5',
    color: '#4a148c',
    border: '#e1bee7',
    shadow: '#ce93d8',
  },
];

const DEFAULT_PROMPTS = [
  { text: "வருவாய்த்துறை நில அளவீடு மற்றும் பட்டா மாறுதல் தொடர்பான அரசு வழிகாட்டுதல்கள் என்ன?", label: "பட்டா & நில அளவீடு" },
  { text: "சமூக பாதுகாப்பு திட்டத்தில் முதியோர் ஓய்வூதியம் (OAP) பெறுவதற்கான தகுதிகள் மற்றும் விண்ணப்பிக்கும் முறை என்ன?", label: "முதியோர் உதவித்தொகை" },
  { text: "பொதுப்பணித்துறை சாலை பராமரிப்பு மற்றும் குடிநீர் விநியோக குறைதீர்க்கும் நெறிமுறைகள் என்ன?", label: "குடிநீர் & சாலை பராமரிப்பு" },
  { text: "அரசு இ-சேவை மூலம் வாரிசுச் சான்றிதழ் மற்றும் வருமானச் சான்றிதழ் பெறும் நடைமுறைகள் என்ன?", label: "அரசு சான்றிதழ்கள்" },
];

export default function GeneralModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();
  const {
    isListening,
    speechLang,
    setSpeechLang,
    startListening,
    stopListening,
    speakText,
    stopSpeech,
    speakingMessageId,
  } = useChatStore();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // Attached Document State
  const [attachedDoc, setAttachedDoc] = useState(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [docSuggestions, setDocSuggestions] = useState([]);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    return () => {
      stopSpeech();
      stopListening();
    };
  }, []);

  // ─── Document Upload & Analysis ──────────────────────────────────
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    try {
      const res = await uploadDocument(file, officerId);
      const suggestions = res.suggestions || [];
      const extractedSuggestions = suggestions.map((s) => ({
        id: s.suggestion_id || `sug_${Date.now()}_${Math.random()}`,
        text: s.text_tamil || s.text_english || s.text || '',
        groundedIn: s.grounded_in || '',
        outputType: s.expected_output_type || 'text',
      }));

      setAttachedDoc({
        sourceId: res.source_id,
        fileName: res.file_name || file.name,
        fileType: res.file_type || 'pdf',
        pageCount: res.page_count || 1,
        fingerprint: res.fingerprint,
      });

      setDocSuggestions(extractedSuggestions);

      // System notification message
      const sysMsg = {
        id: `sys_${Date.now()}`,
        sender: 'ai',
        isDocNotification: true,
        fileName: res.file_name || file.name,
        fileType: res.file_type || 'pdf',
        sourceId: res.source_id,
        text: `📄 **${res.file_name || file.name}** ஆவணம் வெற்றிகரமாக இணைக்கப்பட்டு பகுப்பாய்வு செய்யப்பட்டது.\nஇக்கோப்பின் உள்ளடக்கம் சார்ந்த உடனடி பரிந்துரை வினவல்கள் கீழே தயார் செய்யப்பட்டுள்ளன.`,
        timestamp: new Date().toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch (err) {
      alert(`ஆவண பதிவேற்ற பிழை: ${err.message || 'பதிவேற்ற முடியவில்லை'}`);
    } finally {
      setUploadingDoc(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveAttachedDoc = () => {
    setAttachedDoc(null);
    setDocSuggestions([]);
  };

  // ─── Send Chat Message ──────────────────────────────────────────
  const handleSend = async (textToSend, fromVoice = false) => {
    const messageText = textToSend || input;
    if (!messageText.trim() || loading) return;

    const userMsg = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: messageText.trim(),
      timestamp: new Date().toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const res = await sendChat(
        messageText.trim(),
        officerId,
        attachedDoc ? attachedDoc.sourceId : null,
        attachedDoc ? `Attached File: ${attachedDoc.fileName}` : null
      );

      const aiContent = res.blocks?.[0]?.content || 'செயலாக்கப்பட்டது.';
      const newMsgId = res.message_id || `ai_${Date.now()}`;
      const aiMsg = {
        id: newMsgId,
        sender: 'ai',
        text: aiContent,
        sources: res.sources || [],
        engine: res.engine || null,
        timestamp: new Date().toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMsg]);

      // If officer spoke query, auto-play response in Tamil / English
      if (fromVoice) {
        speakText(newMsgId, aiContent);
      }
    } catch (err) {
      const errorMsg = {
        id: `err_${Date.now()}`,
        sender: 'ai',
        text: `பிழை: ${err.message || 'சேவையகத்தை தொடர்பு கொள்ள முடியவில்லை.'}`,
        timestamp: new Date().toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (sug) => {
    if (sug.id && !sug.id.startsWith('sug_') && !sug.id.startsWith('def_')) {
      trackSuggestionClick(sug.id).catch(() => {});
    }
    handleSend(sug.text);
  };

  // ─── Speech-to-Text (Real-Time Speed-to-Typing Streaming) ────────
  const toggleVoiceInput = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening(
        (interimText) => {
          setInput(interimText);
        },
        (finalText) => {
          if (finalText && finalText.trim()) {
            handleSend(finalText.trim(), true);
          }
        }
      );
    }
  };

  const activeSuggestionsList = attachedDoc && docSuggestions.length > 0
    ? docSuggestions
    : DEFAULT_PROMPTS.map((p, idx) => ({ id: `def_${idx}`, text: p.text, label: p.label }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', gap: 12 }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 className="module-title tamil-text">{t('sidebar.general')}</h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
            ஈரோடு மாவட்ட நிர்வாக தேவைகளுக்கான செயற்கை நுண்ணறிவு உதவியாளர்
          </p>
        </div>

        {/* Right Tools: Language Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            className="btn btn-ghost"
            onClick={() => setSpeechLang(speechLang === 'ta-IN' ? 'en-IN' : 'ta-IN')}
            title="குரல் மொழி மாற்று (Toggle Voice Language)"
            style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <Languages size={15} style={{ color: 'var(--color-tn-accent)' }} />
            <span style={{ fontWeight: 600 }}>{speechLang === 'ta-IN' ? 'தமிழ் (ta-IN)' : 'English (en-IN)'}</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area — Clean and Free of Center Clutter */}
      <div
        className="card"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          padding: '20px 24px',
          position: 'relative',
          background: 'var(--color-surface-card)',
        }}
      >
        {messages.length === 0 ? (
          /* Clean, clutter-free empty state with subtle watermark */
          <div
            style={{
              margin: 'auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: 0.18,
              userSelect: 'none',
              pointerEvents: 'none',
            }}
          >
            <TnEmblem size={96} />
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              style={{
                display: 'flex',
                gap: 12,
                alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}
            >
              {m.sender === 'ai' && (
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    background: 'var(--color-tn-primary)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                  }}
                >
                  <Bot size={18} />
                </div>
              )}
              <div style={{ flex: 1 }}>
                <div
                  className="tamil-text"
                  style={{
                    padding: '14px 18px',
                    borderRadius: 12,
                    background:
                      m.sender === 'user'
                        ? 'var(--color-tn-primary)'
                        : m.isError
                        ? '#fee2e2'
                        : m.isDocNotification
                        ? 'rgba(26, 58, 92, 0.07)'
                        : 'var(--color-surface-hover)',
                    color:
                      m.sender === 'user'
                        ? 'white'
                        : m.isError
                        ? '#991b1b'
                        : 'var(--color-text-primary)',
                    fontSize: '0.9rem',
                    lineHeight: 1.75,
                    whiteSpace: 'pre-wrap',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                    border: m.isDocNotification ? '1px solid rgba(26, 58, 92, 0.15)' : 'none',
                  }}
                >
                  {m.text}
                </div>

                {/* Sources & Controls Below AI Response */}
                {m.sender === 'ai' && (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                      {m.sources && m.sources.map((s, idx) => (
                        <span
                          key={idx}
                          className="tamil-text"
                          style={{
                            fontSize: '0.68rem',
                            background: 'rgba(26, 58, 92, 0.08)',
                            color: 'var(--color-tn-primary)',
                            padding: '2px 8px',
                            borderRadius: 6,
                            border: '1px solid rgba(26, 58, 92, 0.15)',
                          }}
                        >
                          📄 {s}
                        </span>
                      ))}
                      {m.engine && (
                        <span
                          style={{
                            fontSize: '0.65rem',
                            color: 'var(--color-text-muted)',
                            padding: '2px 4px',
                          }}
                        >
                          ⚡ {m.engine}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {!m.isDocNotification && (
                        <button
                          className="btn btn-ghost"
                          onClick={() => speakText(m.id, m.text)}
                          title={speakingMessageId === m.id ? 'பேச்சை நிறுத்து' : 'பதிலை தமிழில் வாசி (Text-to-Speech)'}
                          style={{
                            padding: '3px 8px',
                            fontSize: '0.72rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            color: speakingMessageId === m.id ? '#ef4444' : 'var(--color-tn-primary)',
                          }}
                        >
                          {speakingMessageId === m.id ? <VolumeX size={14} /> : <Volume2 size={14} />}
                          <span>{speakingMessageId === m.id ? 'நிறுத்து' : 'ஒலி வடிவில் கேள்'}</span>
                        </button>
                      )}
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                        {m.timestamp}
                      </span>
                    </div>
                  </div>
                )}

                {m.sender === 'user' && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 4, textAlign: 'right' }}>
                    {m.timestamp}
                  </div>
                )}
              </div>

              {m.sender === 'user' && (
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    background: 'var(--color-surface-hover)',
                    color: 'var(--color-text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <User size={18} />
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div style={{ display: 'flex', gap: 12, alignSelf: 'flex-start' }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: 'var(--color-tn-primary)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Bot size={18} />
            </div>
            <div
              style={{
                padding: '12px 18px',
                borderRadius: 12,
                background: 'var(--color-surface-hover)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
              <span className="tamil-text" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                {attachedDoc ? 'கோப்புத் தகவல்களை ஆய்வு செய்கிறது...' : 'செயலாக்குகிறது...'}
              </span>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* ─── DYNAMIC FLOW-WISE PASTEL SPEECH-BUBBLE PROMPT CHIPS (STACKED VERTICALLY) ─── */}
      {activeSuggestionsList.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            alignItems: 'flex-start',
            padding: '2px 4px 6px',
          }}
        >
          <div
            className="tamil-text"
            style={{
              fontSize: '0.74rem',
              color: 'var(--color-text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontWeight: 600,
              marginBottom: 2,
            }}
          >
            <Sparkles size={13} style={{ color: '#ea580c' }} />
            <span>{attachedDoc ? 'ஆவண வினவல்கள் (பரிந்துரைகள்):' : 'பரிந்துரை வினவல்கள்:'}</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 7, alignItems: 'flex-start', width: '100%' }}>
            {activeSuggestionsList.map((sug, idx) => {
              const palette = PASTEL_BUBBLES[idx % PASTEL_BUBBLES.length];

              return (
                <button
                  key={sug.id || idx}
                  onClick={() => handleSuggestionClick(sug)}
                  className="tamil-text"
                  style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    padding: '8px 16px',
                    borderRadius: '16px 16px 16px 4px', // Speech-bubble tail style
                    background: palette.bg,
                    border: `1.5px solid ${palette.border}`,
                    color: palette.color,
                    boxShadow: `0 2.5px 0 ${palette.shadow}, 0 3px 6px rgba(0,0,0,0.04)`,
                    cursor: 'pointer',
                    transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    maxWidth: '92%',
                    textAlign: 'left',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = `0 4.5px 0 ${palette.shadow}, 0 6px 12px rgba(0,0,0,0.08)`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0px)';
                    e.currentTarget.style.boxShadow = `0 2.5px 0 ${palette.shadow}, 0 3px 6px rgba(0,0,0,0.04)`;
                  }}
                  onMouseDown={(e) => {
                    e.currentTarget.style.transform = 'translateY(1px)';
                    e.currentTarget.style.boxShadow = `0 1px 0 ${palette.shadow}`;
                  }}
                >
                  <span>{sug.text}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ─── INPUT DOCK WITH FILE ATTACH & STREAMING SPEECH ─────────────── */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--color-surface-card)',
          border: '1px solid var(--color-surface-border)',
          borderRadius: 14,
          padding: '10px 14px',
          gap: 8,
          boxShadow: '0 4px 16px rgba(0,0,0,0.03)',
        }}
      >
        {/* Attached Document Pill (if active) */}
        {attachedDoc && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(26, 58, 92, 0.06)',
              border: '1px solid rgba(26, 58, 92, 0.15)',
              borderRadius: 8,
              padding: '4px 10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
              <FileText size={14} style={{ color: 'var(--color-tn-primary)', flexShrink: 0 }} />
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-tn-primary)' }} className="truncate">
                {attachedDoc.fileName}
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>
                ({attachedDoc.fileType.toUpperCase()})
              </span>
            </div>
            <button
              onClick={handleRemoveAttachedDoc}
              title="இணைப்பை நீக்கு"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 2 }}
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Text Area */}
        <textarea
          rows={1}
          placeholder={
            isListening
              ? '🎤 நீங்கள் பேசுவது உடனுக்குடன் பதியப்படுகிறது... (பேசி முடித்ததும் தானாக அனுப்பப்படும்)'
              : attachedDoc
              ? `"${attachedDoc.fileName}" குறித்து கேள்வி கேட்கவும்... (Enter அழுத்தவும்)`
              : 'இங்கே உங்கள் கேள்வியை தட்டச்சு செய்யவும்... (Enter அழுத்தவும்)'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="tamil-text"
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            fontSize: '0.92rem',
            color: 'var(--color-text-primary)',
            resize: 'none',
            padding: '4px 0',
            fontFamily: "'Noto Sans Tamil', sans-serif",
            maxHeight: 120,
          }}
        />

        {/* Bottom Actions inside Dock */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Hidden File Input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.txt"
              style={{ display: 'none' }}
            />

            {/* Attachment Button */}
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingDoc}
              style={{
                fontSize: '0.78rem',
                padding: '6px 10px',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                borderRadius: 8,
                background: attachedDoc ? 'rgba(26, 58, 92, 0.08)' : 'transparent',
              }}
              title="ஆவணத்தை இணைக்கவும் (PDF, Word, Excel, Scan, Text)"
            >
              <Paperclip size={15} style={{ color: attachedDoc ? 'var(--color-tn-primary)' : 'var(--color-text-secondary)' }} />
              <span className="tamil-text">
                {uploadingDoc ? 'பதிவேற்றுகிறது...' : attachedDoc ? 'இணைக்கப்பட்டுள்ளது' : 'இணைப்பு'}
              </span>
            </button>

            {/* Voice Input Button (STT) */}
            <button
              type="button"
              onClick={toggleVoiceInput}
              className={`btn btn-ghost ${isListening ? 'voice-listening-btn' : ''}`}
              style={{
                fontSize: '0.78rem',
                padding: '6px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                borderRadius: 8,
                background: isListening ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.08)',
                color: isListening ? '#ef4444' : '#059669',
                border: isListening ? '1px solid #ef4444' : '1px solid rgba(16, 185, 129, 0.2)',
                transition: 'all 0.2s ease',
              }}
              title={isListening ? 'குரல் பதிவை நிறுத்த கிளிக் செய்யவும்' : 'குரல் மூலம் உள்ளீடு செய்ய கிளிக் செய்யவும் (Speech-to-Text)'}
            >
              {isListening ? <MicOff size={15} /> : <Mic size={15} />}
              <span className="tamil-text">
                {isListening ? 'கேட்கிறது...' : 'குரல் உள்ளீடு'}
              </span>
            </button>
          </div>

          {/* Send Button */}
          <button
            className="btn btn-primary"
            onClick={() => handleSend(null, isListening)}
            disabled={!input.trim() || loading}
            style={{
              padding: '6px 18px',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span className="tamil-text" style={{ fontSize: '0.82rem', fontWeight: 600 }}>அனுப்பு</span>
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
