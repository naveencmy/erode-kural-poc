import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import { sendChat } from '../../lib/api';
import TnEmblem from '../icons/TnEmblem';
import { Send, Bot, User, Sparkles, CornerDownLeft, Paperclip } from 'lucide-react';

const QUICK_PROMPTS = [
  "இன்றைய முக்கிய கோப்புகள் மற்றும் நிலுவை விவரங்கள் என்ன?",
  "வருவாய்த்துறை நில அளவீடு தொடர்பான அரசு வழிகாட்டுதல்கள் என்ன?",
  "சமூக நலத்துறை முதியோர் உதவித்தொகை மனுக்கள் நிலை என்ன?",
  "பொதுமக்களின் பட்டா மாறுதல் மனுவின் சரிபார்ப்பு நடைமுறை என்ன?"
];

export default function GeneralModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
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
      const res = await sendChat(messageText.trim(), officerId);
      const aiContent = res.blocks?.[0]?.content || "செயலாக்கப்பட்டது.";
      const aiMsg = {
        id: res.message_id || `ai_${Date.now()}`,
        sender: 'ai',
        text: aiContent,
        timestamp: new Date().toLocaleTimeString('ta-IN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMsg]);
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="module-title tamil-text">{t('sidebar.general')}</h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
            ஈரோடு மாவட்ட நிர்வாக தேவைகளுக்கான செயற்கை நுண்ணறிவு உதவியாளர்
          </p>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        className="card"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          padding: 24,
          position: 'relative',
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: 500, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
            <TnEmblem size={80} opacity={0.25} className="text-[#1a3a5c] dark:text-[#c8a951]" />
            <h3 className="tamil-text" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              வணக்கம், அலுவலர் {officerId}!
            </h3>
            <p className="tamil-text" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              மாவட்ட நிர்வாக வினவல்கள், விதிமுறைகள், மனுக்கள் குறித்த வழிகாட்டுதல்களை கேட்கலாம்.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', marginTop: 8 }}>
              {QUICK_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="btn btn-ghost tamil-text"
                  style={{ textAlign: 'left', justifyContent: 'flex-start', fontSize: '0.8rem', padding: '10px 14px' }}
                  onClick={() => handleSend(prompt)}
                >
                  <Sparkles size={14} style={{ color: 'var(--color-tn-accent)', flexShrink: 0 }} />
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
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
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: 'var(--color-tn-primary)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Bot size={18} />
                </div>
              )}
              <div>
                <div
                  className="tamil-text"
                  style={{
                    padding: '12px 18px',
                    borderRadius: 12,
                    background:
                      m.sender === 'user'
                        ? 'var(--color-tn-primary)'
                        : m.isError
                        ? '#fee2e2'
                        : 'var(--color-surface-hover)',
                    color:
                      m.sender === 'user'
                        ? 'white'
                        : m.isError
                        ? '#991b1b'
                        : 'var(--color-text-primary)',
                    fontSize: '0.9rem',
                    lineHeight: 1.7,
                    whiteSpace: 'pre-wrap',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.05)',
                  }}
                >
                  {m.text}
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'var(--color-text-muted)',
                    marginTop: 4,
                    textAlign: m.sender === 'user' ? 'right' : 'left',
                  }}
                >
                  {m.timestamp}
                </div>
              </div>
              {m.sender === 'user' && (
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
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
                width: 32,
                height: 32,
                borderRadius: 8,
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
                செயலாக்குகிறது...
              </span>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          background: 'var(--color-surface-card)',
          border: '1px solid var(--color-surface-border)',
          borderRadius: 12,
          padding: '8px 14px',
          alignItems: 'flex-end',
        }}
      >
        <textarea
          rows={1}
          placeholder="இங்கே உங்கள் கேள்வியை தட்டச்சு செய்யவும்... (Enter அழுத்தவும்)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="tamil-text"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            fontSize: '0.9rem',
            color: 'var(--color-text-primary)',
            resize: 'none',
            padding: '6px 0',
            fontFamily: "'Noto Sans Tamil', sans-serif",
            maxHeight: 120,
          }}
        />
        <button
          className="btn btn-primary"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          style={{ padding: '8px 16px', borderRadius: 8 }}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
