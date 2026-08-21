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
  XCircle,
  AlertCircle,
  Paperclip,
  ArrowRight,
  Shield,
  ExternalLink,
} from 'lucide-react';

export default function MailModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();

  const [activeTab, setActiveTab] = useState('inbox'); // 'inbox' | 'compose' | 'sent'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Inbox state
  const [receivedEmails, setReceivedEmails] = useState([]);
  const [ingestingUid, setIngestingUid] = useState(null);

  // Compose state
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);

  // Sent logs state
  const [sentLogs, setSentLogs] = useState([]);

  useEffect(() => {
    loadInbox();
    loadSentLogs();
  }, []);

  const loadInbox = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReceivedEmails(20);
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
      console.warn("Could not load sent logs:", err);
    }
  };

  const handleIngestEmail = async (uid) => {
    setIngestingUid(uid);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await ingestEmailToWorkflow(uid, officerId);
      setSuccessMsg(`மின்னஞ்சல் மனுவாக உட்கொள்ளப்பட்டது! Source ID: ${res.source_id}`);
      await loadInbox();
    } catch (err) {
      setError(err.message);
    } finally {
      setIngestingUid(null);
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    if (!composeTo.trim() || !composeSubject.trim() || !composeBody.trim()) {
      setError("பெறுநர் முகவரி, தலைப்பு மற்றும் உள்ளடக்கத்தை உள்ளிடவும்.");
      return;
    }
    setSending(true);
    setError(null);
    setSendResult(null);
    try {
      const res = await sendOfficialEmail({
        recipient_email: composeTo.trim(),
        subject: composeSubject.trim(),
        body: composeBody.trim(),
        officer_id: officerId || 'OFFICER',
      });
      setSendResult(res);
      setSuccessMsg(`மின்னஞ்சல் வெற்றிகரமாக அனுப்பப்பட்டது (${composeTo})`);
      setComposeTo('');
      setComposeSubject('');
      setComposeBody('');
      await loadSentLogs();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="module-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div className="module-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 className="module-title tamil-text" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Mail className="text-tn-accent" size={24} />
            மின்னஞ்சல் மையம் (Email & Official Mail Hub)
          </h2>
          <p className="module-subtitle tamil-text">
            மனுதாரர் மின்னஞ்சல்களை உட்கொள்ளுதல், Brevo கிளவுட் வழியாக பாதுகாப்பாக அதிகாரப்பூர்வ ஒப்புகை கடிதம் அனுப்புதல்
          </p>
        </div>

        {/* Global Action */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              if (activeTab === 'inbox') loadInbox();
              if (activeTab === 'sent') loadSentLogs();
            }}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span className="tamil-text">புதுப்பி (Refresh)</span>
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className="alert alert-success animate-fade-in" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CheckCircle2 size={16} />
          <span className="tamil-text" style={{ fontSize: '0.875rem' }}>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', opacity: 0.7 }}
          >
            ×
          </button>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="alert alert-danger animate-fade-in" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertCircle size={16} />
          <span className="tamil-text" style={{ fontSize: '0.875rem' }}>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', opacity: 0.7 }}
          >
            ×
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 0 }}>
        <button
          className={`tab tamil-text ${activeTab === 'inbox' ? 'active' : ''}`}
          onClick={() => setActiveTab('inbox')}
        >
          <Inbox size={14} style={{ display: 'inline', marginRight: 6 }} />
          பெறப்பட்ட அஞ்சல்கள் (Received Inbox) ({receivedEmails.length})
        </button>
        <button
          className={`tab tamil-text ${activeTab === 'compose' ? 'active' : ''}`}
          onClick={() => setActiveTab('compose')}
        >
          <Send size={14} style={{ display: 'inline', marginRight: 6 }} />
          மின்னஞ்சல் அனுப்புதல் (Compose & Send)
        </button>
        <button
          className={`tab tamil-text ${activeTab === 'sent' ? 'active' : ''}`}
          onClick={() => setActiveTab('sent')}
        >
          <History size={14} style={{ display: 'inline', marginRight: 6 }} />
          அனுப்பப்பட்ட பதிவேடு (Sent History) ({sentLogs.length})
        </button>
      </div>

      {/* ─── TAB 1: RECEIVED INBOX ─────────────────────────────────────────── */}
      {activeTab === 'inbox' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {receivedEmails.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
              <Inbox size={36} style={{ margin: '0 auto 10px' }} />
              <p className="tamil-text" style={{ fontSize: '0.95rem' }}>பெறப்பட்ட மின்னஞ்சல்கள் ஏதுமில்லை.</p>
            </div>
          ) : (
            receivedEmails.map((eml) => (
              <div
                key={eml.uid}
                className="card"
                style={{
                  padding: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 16,
                  transition: 'transform 0.15s ease',
                }}
              >
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)' }} className="tamil-text">
                      {eml.subject}
                    </span>
                    {eml.has_attachments && (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: '0.75rem',
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: 'var(--color-surface-hover)',
                        color: 'var(--color-text-secondary)',
                      }}>
                        <Paperclip size={11} />
                        {eml.attachments?.length || 1} இணைப்புகள்
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 16, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                    <span><strong>அனுப்பியவர்:</strong> {eml.sender}</span>
                    <span><strong>நாள்:</strong> {eml.date}</span>
                  </div>

                  <p className="tamil-text" style={{
                    fontSize: '0.85rem',
                    color: 'var(--color-text-secondary)',
                    margin: '4px 0 0 0',
                    lineHeight: 1.5,
                  }}>
                    {eml.snippet}...
                  </p>
                </div>

                {/* 1-Click Action */}
                <div>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={ingestingUid === eml.uid}
                    onClick={() => handleIngestEmail(eml.uid)}
                    title="இந்த மின்னஞ்சலை தானியங்கி மனுவாக மொத்த பணிப்பாய்வில் சேர்க்கவும்"
                    style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    <ArrowRight size={14} />
                    <span>{ingestingUid === eml.uid ? 'உட்கொள்கிறது...' : 'மனுவாக மாற்று (Ingest)'}</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ─── TAB 2: COMPOSE & SEND ───────────────────────────────────────── */}
      {activeTab === 'compose' && (
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Active Cloud Relay Status Banner */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderRadius: 8,
            background: 'var(--color-surface-hover)',
            border: '1px solid var(--color-surface-border)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Shield size={18} className="text-tn-accent" />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
                  Brevo Cloud Transactional SMTP Relay
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                  அனுப்புநர் (Sender): <code>naveenatdevine@gmail.com</code> (பாதுகாப்பானது / Secured via .env)
                </div>
              </div>
            </div>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '4px 10px',
              borderRadius: 20,
              background: '#dcfce7',
              color: '#166534',
            }}>
              🟢 செயலில் உள்ளது (Active)
            </span>
          </div>

          <form onSubmit={handleSendEmail} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                பெறுநர் மின்னஞ்சல் (Citizen / Officer Email) *
              </label>
              <input
                type="email"
                required
                placeholder="எ.கா: citizen.erode@gmail.com"
                value={composeTo}
                onChange={(e) => setComposeTo(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)',
                  color: 'var(--color-text-primary)',
                  fontSize: '0.9rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }} className="tamil-text">
                மின்னஞ்சல் தலைப்பு (Subject) *
              </label>
              <input
                type="text"
                required
                placeholder="எ.கா: மனு எண் 1001/REV/2026 - ஒப்புகைச் சீட்டு (Acknowledgement)"
                value={composeSubject}
                onChange={(e) => setComposeSubject(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)',
                  color: 'var(--color-text-primary)',
                  fontSize: '0.9rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }} className="tamil-text">
                அதிகாரப்பூர்வ செய்தி / ஒப்புகை விவரம் (Tamil Body) *
              </label>
              <textarea
                required
                rows={8}
                placeholder="மதிப்பிற்குரிய மனுதாரர் அவர்களுக்கு, தங்கள் மனு பெறப்பட்டு கோப்பு எண் ஒதுக்கீடு செய்யப்பட்டுள்ளது..."
                value={composeBody}
                onChange={(e) => setComposeBody(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)',
                  color: 'var(--color-text-primary)',
                  fontSize: '0.9rem',
                  lineHeight: 1.7,
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={sending}
                style={{ padding: '12px 24px' }}
              >
                <Send size={16} />
                <span className="tamil-text">{sending ? 'அனுப்புகிறது...' : 'மின்னஞ்சல் அனுப்பு (Send Official Mail)'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ─── TAB 3: SENT HISTORY ─────────────────────────────────────────── */}
      {activeTab === 'sent' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>பெறுநர் (Recipient)</th>
                <th>தலைப்பு (Subject)</th>
                <th>அனுப்பிய நேரம் (Timestamp)</th>
                <th>கோப்பு எண் (Source ID)</th>
                <th>நிலை (Status)</th>
              </tr>
            </thead>
            <tbody>
              {sentLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 30, color: 'var(--color-text-muted)' }}>
                    அனுப்பப்பட்ட பதிவேடுகள் ஏதுமில்லை (No sent email history).
                  </td>
                </tr>
              ) : (
                sentLogs.map((log, idx) => (
                  <tr key={log.email_id || log.id || idx}>
                    <td style={{ fontWeight: 600 }}>{log.recipient_email}</td>
                    <td className="tamil-text">{log.subject}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>{log.sent_at}</td>
                    <td><code>{log.source_id ? log.source_id.slice(0, 10) : '—'}</code></td>
                    <td>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        background: log.status === 'sent' ? '#dcfce7' : '#fee2e2',
                        color: log.status === 'sent' ? '#166534' : '#991b1b',
                      }}>
                        {log.status === 'sent' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                        {log.status === 'sent' ? 'வெற்றிகரமாக அனுப்பப்பட்டது' : 'தோல்வி'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
