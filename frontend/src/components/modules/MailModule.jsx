import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import {
  fetchReceivedEmails,
  ingestEmailToWorkflow,
  sendOfficialEmail,
  fetchSentEmailLogs,
} from '../../lib/api';
import {
  Mail,
  Inbox,
  Send,
  History,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Paperclip,
  ArrowRight,
  Shield,
  Search,
} from 'lucide-react';

const MAIL_TEMPLATES = [
  {
    id: 'ack',
    title: 'மனு ஒப்புகைச் சீட்டு (Grievance Acknowledgement)',
    subject: 'ஈரோடு மாவட்ட ஆட்சியரகம் - மனு ஒப்புகைச் சீட்டு',
    body: `வணக்கம்,\n\nதங்களால் சமர்ப்பிக்கப்பட்ட மனு பெறப்பட்டு, ஈரோடு மாவட்ட ஆட்சியரக கோப்பு எண் 1042/REV/2026 ஒதுக்கீடு செய்யப்பட்டுள்ளது.\n\nமனுவின் நிலை குறித்த விசாரணை நடைபெற்று வருகிறது. உரிய காலத்தில் நடவடிக்கை மேற்கொள்ளப்படும்.\n\nஇப்படிக்கு,\nமாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.`,
  },
  {
    id: 'docs_req',
    title: 'கூடுதல் ஆவணங்கள் கோருதல் (Request Additional Proof)',
    subject: 'ஈரோடு மாவட்ட ஆட்சியரகம் - கூடுதல் ஆவணங்கள் சமர்ப்பிக்க கோருதல்',
    body: `வணக்கம்,\n\nதங்கள் மனு பரிசீலனையில் உள்ளது. மனு மீதான அடுத்தகட்ட நடவடிக்கைக்கு தங்களின் நில உரிமை ஆவணங்கள் / ஆதார் நகல் ஆகியவற்றை சம்பந்தப்பட்ட வட்டாட்சியர் அலுவலகத்தில் சமர்ப்பிக்க வேண்டுகிறோம்.\n\nஇப்படிக்கு,\nமாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.`,
  },
  {
    id: 'inquiry',
    title: 'கள விசாரணை அறிவிப்பு (Field Inquiry Notice)',
    subject: 'ஈரோடு மாவட்ட ஆட்சியரகம் - கள விசாரணை குறித்த அறிவிப்பு',
    body: `வணக்கம்,\n\nதங்கள் மனு தொடர்பாக கிராம நிர்வாக அலுவலர் (VAO) மற்றும் வருவாய் ஆய்வாளர் (RI) அவர்களால் கள ஆய்வு மேற்கொள்ளப்பட உள்ளது. தாங்கள் உரிய ஆவணங்களுடன் நேரில் இருக்கக் கேட்டுக்கொள்ளப்படுகிறீர்கள்.\n\nஇப்படிக்கு,\nமாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.`,
  },
];

export default function MailModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();

  const [activeTab, setActiveTab] = useState('inbox'); // 'inbox' | 'compose' | 'sent'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Inbox & Filter state
  const [receivedEmails, setReceivedEmails] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [ingestingUid, setIngestingUid] = useState(null);

  // Compose state
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sending, setSending] = useState(false);

  // Sent logs state
  const [sentLogs, setSentLogs] = useState([]);
  const [sentSearchQuery, setSentSearchQuery] = useState('');

  useEffect(() => {
    loadInbox();
    loadSentLogs();
  }, []);

  const loadInbox = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReceivedEmails(30);
      setReceivedEmails(res.emails || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSentLogs = async () => {
    try {
      const res = await fetchSentEmailLogs(50);
      setSentLogs(res.sent_emails || []);
    } catch (err) {
      console.warn('Could not load sent logs:', err);
    }
  };

  const handleIngestEmail = async (uid, e) => {
    if (e) e.stopPropagation();
    setIngestingUid(uid);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await ingestEmailToWorkflow(uid, officerId);
      setSuccessMsg(`மின்னஞ்சல் மனுவாக உட்கொள்ளப்பட்டது! கோப்பு எண்: ${res.source_id}`);
      await loadInbox();
    } catch (err) {
      setError(err.message);
    } finally {
      setIngestingUid(null);
    }
  };

  const applyTemplate = (tpl) => {
    setComposeSubject(tpl.subject);
    setComposeBody(tpl.body);
  };

  const handleQuickReply = (email) => {
    setActiveTab('compose');
    setComposeTo(email.sender_email || email.sender);
    setComposeSubject(`மறுமொழி: ${email.subject}`);
    setComposeBody(`மதிப்பிற்குரிய மனுதாரர் அவர்களுக்கு,\n\nதங்கள் மின்னஞ்சல் (${email.subject}) பெறப்பட்டது. இது தொடர்பாக...`);
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    if (!composeTo.trim() || !composeSubject.trim() || !composeBody.trim()) {
      setError('பெறுநர் முகவரி, தலைப்பு மற்றும் உள்ளடக்கத்தை உள்ளிடவும்.');
      return;
    }
    setSending(true);
    setError(null);
    try {
      await sendOfficialEmail({
        recipient_email: composeTo.trim(),
        subject: composeSubject.trim(),
        body: composeBody.trim(),
        officer_id: officerId || 'OFFICER',
      });
      setSuccessMsg(`அதிகாரப்பூர்வ மின்னஞ்சல் வெற்றிகரமாக அனுப்பப்பட்டது (${composeTo})`);
      setComposeTo('');
      setComposeSubject('');
      setComposeBody('');
      await loadSentLogs();
      setActiveTab('sent');
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  // Filtered lists
  const filteredInbox = receivedEmails.filter((eml) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (eml.subject || '').toLowerCase().includes(q) ||
      (eml.sender || '').toLowerCase().includes(q) ||
      (eml.body || '').toLowerCase().includes(q)
    );
  });

  const filteredSent = sentLogs.filter((log) => {
    if (!sentSearchQuery.trim()) return true;
    const q = sentSearchQuery.toLowerCase();
    return (
      (log.recipient || '').toLowerCase().includes(q) ||
      (log.subject || '').toLowerCase().includes(q) ||
      (log.source_id || '').toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, height: 'calc(100vh - 120px)', width: '100%' }}>
      {/* Module Header Card */}
      <div
        className="card"
        style={{
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          background: 'var(--color-surface-card)',
          borderRadius: 14,
          border: '1px solid var(--color-surface-border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'rgba(234, 88, 12, 0.1)',
              color: '#ea580c',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Mail size={24} />
          </div>
          <div>
            <h2 className="tamil-text" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>
              மின்னஞ்சல் மையம் (Email & Official Mail Hub)
            </h2>
            <p className="tamil-text" style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', marginTop: 2 }}>
              மனுதாரர் மின்னஞ்சல்களை உட்கொள்ளுதல், Brevo கிளவுட் வழியாக பாதுகாப்பாக அதிகாரப்பூர்வ ஒப்புகை கடிதம் அனுப்புதல்
            </p>
          </div>
        </div>

        <button
          className="btn btn-ghost"
          onClick={() => {
            if (activeTab === 'inbox') loadInbox();
            if (activeTab === 'sent') loadSentLogs();
          }}
          disabled={loading}
          style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span className="tamil-text">புதுப்பி (Refresh)</span>
        </button>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 10,
            background: 'rgba(34, 197, 94, 0.12)',
            border: '1px solid #22c55e',
            color: '#15803d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.84rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} />
            <span className="tamil-text">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
      )}

      {error && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 10,
            background: '#fee2e2',
            border: '1px solid #ef4444',
            color: '#991b1b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.84rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={16} />
            <span className="tamil-text">{error}</span>
          </div>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
      )}

      {/* Tabs Bar */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          borderBottom: '1px solid var(--color-surface-border)',
          paddingBottom: 2,
        }}
      >
        <button
          onClick={() => setActiveTab('inbox')}
          className="tamil-text"
          style={{
            padding: '8px 18px',
            borderRadius: '8px 8px 0 0',
            border: 'none',
            background: activeTab === 'inbox' ? 'var(--color-surface-card)' : 'transparent',
            borderBottom: activeTab === 'inbox' ? '2px solid var(--color-tn-primary)' : '2px solid transparent',
            color: activeTab === 'inbox' ? 'var(--color-tn-primary)' : 'var(--color-text-secondary)',
            fontWeight: activeTab === 'inbox' ? 700 : 500,
            fontSize: '0.86rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Inbox size={15} />
          <span>பெறப்பட்ட அஞ்சல்கள் (Received Inbox)</span>
          <span
            style={{
              fontSize: '0.72rem',
              background: 'rgba(26, 58, 92, 0.1)',
              padding: '2px 8px',
              borderRadius: 10,
              fontWeight: 700,
            }}
          >
            {receivedEmails.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('compose')}
          className="tamil-text"
          style={{
            padding: '8px 18px',
            borderRadius: '8px 8px 0 0',
            border: 'none',
            background: activeTab === 'compose' ? 'var(--color-surface-card)' : 'transparent',
            borderBottom: activeTab === 'compose' ? '2px solid var(--color-tn-primary)' : '2px solid transparent',
            color: activeTab === 'compose' ? 'var(--color-tn-primary)' : 'var(--color-text-secondary)',
            fontWeight: activeTab === 'compose' ? 700 : 500,
            fontSize: '0.86rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Send size={15} />
          <span>மின்னஞ்சல் அனுப்புதல் (Compose & Send)</span>
        </button>

        <button
          onClick={() => setActiveTab('sent')}
          className="tamil-text"
          style={{
            padding: '8px 18px',
            borderRadius: '8px 8px 0 0',
            border: 'none',
            background: activeTab === 'sent' ? 'var(--color-surface-card)' : 'transparent',
            borderBottom: activeTab === 'sent' ? '2px solid var(--color-tn-primary)' : '2px solid transparent',
            color: activeTab === 'sent' ? 'var(--color-tn-primary)' : 'var(--color-text-secondary)',
            fontWeight: activeTab === 'sent' ? 700 : 500,
            fontSize: '0.86rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <History size={15} />
          <span>அனுப்பப்பட்ட பதிவேடு (Sent History)</span>
          <span
            style={{
              fontSize: '0.72rem',
              background: 'rgba(26, 58, 92, 0.1)',
              padding: '2px 8px',
              borderRadius: 10,
              fontWeight: 700,
            }}
          >
            {sentLogs.length}
          </span>
        </button>
      </div>

      {/* ─── TAB 1: INBOX VIEW (FULL WIDTH) ───────────────────────────── */}
      {activeTab === 'inbox' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', flex: 1 }}>
          {/* Search Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--color-surface-card)',
              border: '1px solid var(--color-surface-border)',
              borderRadius: 10,
              padding: '8px 14px',
              gap: 10,
            }}
          >
            <Search size={16} style={{ color: 'var(--color-text-muted)' }} />
            <input
              type="text"
              placeholder="மின்னஞ்சல் தலைப்பு, அனுப்புநர் அல்லது உள்ளடக்கத்தை தேடவும்..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="tamil-text"
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                fontSize: '0.88rem',
                color: 'var(--color-text-primary)',
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Email Cards List */}
          {filteredInbox.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
              <Inbox size={40} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
              <p className="tamil-text" style={{ fontSize: '0.95rem' }}>பொருந்தும் மின்னஞ்சல்கள் ஏதுமில்லை.</p>
            </div>
          ) : (
            filteredInbox.map((eml) => {
              const isIngesting = ingestingUid === eml.uid;

              return (
                <div
                  key={eml.uid}
                  className="card"
                  style={{
                    padding: '16px 20px',
                    borderRadius: 12,
                    border: '1px solid var(--color-surface-border)',
                    background: 'var(--color-surface-card)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: 16,
                  }}
                >
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, overflow: 'hidden' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <span
                        className="tamil-text truncate"
                        style={{
                          fontWeight: 700,
                          fontSize: '0.96rem',
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {eml.subject || '(தலைப்பு இல்லை)'}
                      </span>
                      {eml.has_attachments && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 8px',
                            borderRadius: 4,
                            background: 'var(--color-surface-hover)',
                            color: 'var(--color-text-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Paperclip size={11} />
                          {eml.attachments?.length || 1} இணைப்புகள்
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: 16, fontSize: '0.8rem', color: 'var(--color-text-secondary)', flexWrap: 'wrap' }}>
                      <span>
                        <strong>அனுப்பியவர்:</strong> {eml.sender}
                      </span>
                      <span>
                        <strong>நாள்:</strong> {eml.date}
                      </span>
                    </div>

                    <p
                      className="tamil-text"
                      style={{
                        fontSize: '0.82rem',
                        color: 'var(--color-text-secondary)',
                        lineHeight: 1.5,
                        marginTop: 2,
                      }}
                    >
                      {eml.snippet || eml.body || ''}
                    </p>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end', flexShrink: 0 }}>
                    <button
                      className="btn btn-primary"
                      onClick={(e) => handleIngestEmail(eml.uid, e)}
                      disabled={isIngesting}
                      style={{
                        fontSize: '0.78rem',
                        padding: '7px 14px',
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        whiteSpace: 'nowrap',
                      }}
                      title="இம்மின்னஞ்சலை கோப்பு மனுவாக மாற்றி பகுப்பாய்வு செய்க"
                    >
                      {isIngesting ? (
                        <>
                          <div className="spinner" style={{ width: 12, height: 12 }} />
                          <span>உட்கொள்ளுகிறது...</span>
                        </>
                      ) : (
                        <>
                          <span className="tamil-text">மனுவாக மாற்று (Ingest)</span>
                          <ArrowRight size={14} />
                        </>
                      )}
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleQuickReply(eml)}
                      style={{ fontSize: '0.75rem', padding: '4px 10px', color: 'var(--color-tn-primary)' }}
                    >
                      மறுமொழி அனுப்பு
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ─── TAB 2: COMPOSE VIEW ───────────────────────────────────────── */}
      {activeTab === 'compose' && (
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto', flex: 1 }}>
          {/* Brevo SMTP Status Banner */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              background: 'rgba(34, 197, 94, 0.08)',
              border: '1px solid rgba(34, 197, 94, 0.25)',
              borderRadius: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Shield size={20} style={{ color: '#15803d' }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#15803d' }}>
                  Brevo Cloud Transactional SMTP Relay
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                  அனுப்புநர் (Sender): naveenatdevine@gmail.com (பாதுகாப்பானது / Secured via .env)
                </div>
              </div>
            </div>
            <span
              style={{
                fontSize: '0.74rem',
                fontWeight: 700,
                color: '#15803d',
                background: 'rgba(34, 197, 94, 0.15)',
                padding: '4px 10px',
                borderRadius: 12,
              }}
            >
              ● செயலில் உள்ளது [Active]
            </span>
          </div>

          {/* Quick Templates Selector */}
          <div>
            <div className="tamil-text" style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 8, fontWeight: 600 }}>
              அரசாங்க அஞ்சல் வார்ப்புருக்கள் (Quick Templates):
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {MAIL_TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => applyTemplate(t)}
                  className="tamil-text"
                  style={{
                    fontSize: '0.76rem',
                    padding: '6px 14px',
                    borderRadius: 16,
                    background: 'var(--color-surface-hover)',
                    border: '1px solid var(--color-surface-border)',
                    color: 'var(--color-text-primary)',
                    cursor: 'pointer',
                  }}
                >
                  📝 {t.title}
                </button>
              ))}
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSendEmail} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label className="tamil-text" style={{ fontSize: '0.84rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                பெறுநர் மின்னஞ்சல் (Citizen / Officer Email) *
              </label>
              <input
                type="email"
                placeholder="எ.கா: citizen.erode@gmail.com"
                value={composeTo}
                onChange={(e) => setComposeTo(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-bg)',
                  fontSize: '0.88rem',
                  color: 'var(--color-text-primary)',
                  outline: 'none',
                }}
                required
              />
            </div>

            <div>
              <label className="tamil-text" style={{ fontSize: '0.84rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                மின்னஞ்சல் தலைப்பு (Subject) *
              </label>
              <input
                type="text"
                placeholder="எ.கா: மனு எண் 1001/REV/2026 - ஒப்புகைச் சீட்டு (Acknowledgement)"
                value={composeSubject}
                onChange={(e) => setComposeSubject(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-bg)',
                  fontSize: '0.88rem',
                  color: 'var(--color-text-primary)',
                  outline: 'none',
                }}
                required
              />
            </div>

            <div>
              <label className="tamil-text" style={{ fontSize: '0.84rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                அதிகாரப்பூர்வ செய்தி / ஒப்புகை விவரம் (Tamil Body) *
              </label>
              <textarea
                rows={9}
                placeholder="மதிப்பிற்குரிய மனுதாரர் அவர்களுக்கு, தங்கள் மனு பெறப்பட்டு கோப்பு எண் ஒதுக்கீடு செய்யப்பட்டுள்ளது..."
                value={composeBody}
                onChange={(e) => setComposeBody(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-bg)',
                  fontSize: '0.88rem',
                  color: 'var(--color-text-primary)',
                  outline: 'none',
                  lineHeight: 1.6,
                  resize: 'vertical',
                }}
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={sending}
                style={{ padding: '10px 28px', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}
              >
                {sending ? (
                  <>
                    <div className="spinner" style={{ width: 14, height: 14 }} />
                    <span className="tamil-text">அனுப்புகிறது...</span>
                  </>
                ) : (
                  <>
                    <Send size={15} />
                    <span className="tamil-text" style={{ fontWeight: 700 }}>
                      மின்னஞ்சல் அனுப்பு (Send Official Mail)
                    </span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ─── TAB 3: SENT HISTORY VIEW ──────────────────────────────────── */}
      {activeTab === 'sent' && (
        <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14, overflowY: 'auto', flex: 1 }}>
          {/* Search */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--color-surface-bg)',
              border: '1px solid var(--color-surface-border)',
              borderRadius: 8,
              padding: '8px 14px',
              gap: 8,
            }}
          >
            <Search size={15} style={{ color: 'var(--color-text-muted)' }} />
            <input
              type="text"
              placeholder="அனுப்பப்பட்ட பெறுநர், தலைப்பு அல்லது கோப்பு எண் தேடவும்..."
              value={sentSearchQuery}
              onChange={(e) => setSentSearchQuery(e.target.value)}
              className="tamil-text"
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                fontSize: '0.84rem',
                color: 'var(--color-text-primary)',
              }}
            />
          </div>

          {/* Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
              <thead>
                <tr style={{ borderBottom: '1.5px solid var(--color-surface-border)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 8px', color: 'var(--color-text-secondary)' }}>பெறுநர் (RECIPIENT)</th>
                  <th style={{ padding: '10px 8px', color: 'var(--color-text-secondary)' }}>தலைப்பு (SUBJECT)</th>
                  <th style={{ padding: '10px 8px', color: 'var(--color-text-secondary)' }}>அனுப்பிய நேரம் (TIMESTAMP)</th>
                  <th style={{ padding: '10px 8px', color: 'var(--color-text-secondary)' }}>கோப்பு எண் (SOURCE ID)</th>
                  <th style={{ padding: '10px 8px', color: 'var(--color-text-secondary)', textAlign: 'right' }}>நிலை (STATUS)</th>
                </tr>
              </thead>
              <tbody>
                {filteredSent.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: 30, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      அனுப்பப்பட்ட பதிவுகள் ஏதுமில்லை.
                    </td>
                  </tr>
                ) : (
                  filteredSent.map((log, idx) => {
                    const isSuccess = log.status === 'sent' || log.status === 'success';
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--color-surface-border)' }}>
                        <td style={{ padding: '10px 8px', fontWeight: 600 }}>{log.recipient || '—'}</td>
                        <td style={{ padding: '10px 8px' }} className="tamil-text truncate max-w-xs">
                          {log.subject || '—'}
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>
                          {log.timestamp || log.sent_at || '—'}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: 'monospace', fontSize: '0.76rem' }}>
                          {log.source_id || '—'}
                        </td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}>
                          <span
                            className="tamil-text"
                            style={{
                              fontSize: '0.74rem',
                              padding: '3px 10px',
                              borderRadius: 10,
                              background: isSuccess ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                              color: isSuccess ? '#15803d' : '#b91c1c',
                              fontWeight: 600,
                            }}
                          >
                            {isSuccess ? '● வெற்றிகரமாக அனுப்பப்பட்டது' : '● தோல்வி'}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
