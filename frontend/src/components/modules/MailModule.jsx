import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import {
  testMailConnection,
  fetchReceivedEmails,
  ingestEmailToWorkflow,
  sendOfficialEmail,
  fetchSentEmailLogs,
  fetchMailConfig,
  saveMailConfig,
} from '../../lib/api';
import {
  Mail,
  Inbox,
  Send,
  History,
  Settings,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Paperclip,
  ArrowRight,
  Shield,
  Server,
  Sparkles,
  ExternalLink,
  Save,
} from 'lucide-react';


const PRESETS = {
  nic: {
    name: "🏛️ NIC அரசு மின்னஞ்சல் (NIC Mail)",
    imap_server: "imap.nic.in",
    imap_port: 993,
    smtp_server: "smtp.nic.in",
    smtp_port: 587,
    smtp_tls: true,
    smtp_ssl: false,
    from_email: "collectorate.erode@tn.gov.in",
  },
  gmail: {
    name: "✉️ Google Workspace / Gmail",
    imap_server: "imap.gmail.com",
    imap_port: 993,
    smtp_server: "smtp.gmail.com",
    smtp_port: 587,
    smtp_tls: true,
    smtp_ssl: false,
    from_email: "erode.collectorate@gmail.com",
  },
  outlook: {
    name: "🏢 Microsoft 365 / Outlook",
    imap_server: "outlook.office365.com",
    imap_port: 993,
    smtp_server: "smtp.office365.com",
    smtp_port: 587,
    smtp_tls: true,
    smtp_ssl: false,
    from_email: "collectorate@erode.tn.gov.in",
  },
};

export default function MailModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();

  const [activeTab, setActiveTab] = useState('inbox'); // 'inbox' | 'compose' | 'sent' | 'settings'
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

  // Config & Test state
  const [mailConfig, setMailConfig] = useState({
    imap_server: 'imap.nic.in',
    imap_port: 993,
    imap_user: '',
    imap_password: '',
    smtp_server: 'smtp.nic.in',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_tls: true,
    smtp_ssl: false,
    from_email: 'collectorate.erode@tn.gov.in',
    from_name: 'ஈரோடு மாவட்ட ஆட்சியரகம்',
  });
  const [testResults, setTestResults] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);

  useEffect(() => {
    loadInbox();
    loadConfig();
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

  const loadConfig = async () => {
    try {
      const res = await fetchMailConfig();
      if (res) {
        setMailConfig((prev) => ({ ...prev, ...res, imap_password: '', smtp_password: '' }));
      }
    } catch (err) {
      console.warn("Could not load mail config:", err);
    }
  };

  const handleApplyPreset = (presetKey) => {
    const p = PRESETS[presetKey];
    if (!p) return;
    setMailConfig((prev) => ({
      ...prev,
      imap_server: p.imap_server,
      imap_port: p.imap_port,
      smtp_server: p.smtp_server,
      smtp_port: p.smtp_port,
      smtp_tls: p.smtp_tls,
      smtp_ssl: p.smtp_ssl,
      from_email: p.from_email || prev.from_email,
    }));
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResults(null);
    setError(null);
    try {
      const res = await testMailConnection({
        imap_server: mailConfig.imap_server,
        imap_port: Number(mailConfig.imap_port),
        imap_user: mailConfig.imap_user,
        imap_password: mailConfig.imap_password || undefined,
        smtp_server: mailConfig.smtp_server,
        smtp_port: Number(mailConfig.smtp_port),
        smtp_user: mailConfig.smtp_user || mailConfig.imap_user,
        smtp_password: mailConfig.smtp_password || mailConfig.imap_password || undefined,
        smtp_tls: mailConfig.smtp_tls,
        smtp_ssl: mailConfig.smtp_ssl,
      });
      setTestResults(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await saveMailConfig({
        imap_server: mailConfig.imap_server,
        imap_port: Number(mailConfig.imap_port),
        imap_user: mailConfig.imap_user,
        imap_password: mailConfig.imap_password || undefined,
        smtp_server: mailConfig.smtp_server,
        smtp_port: Number(mailConfig.smtp_port),
        smtp_user: mailConfig.smtp_user || mailConfig.imap_user,
        smtp_password: mailConfig.smtp_password || mailConfig.imap_password || undefined,
        smtp_tls: mailConfig.smtp_tls,
        smtp_ssl: mailConfig.smtp_ssl,
        from_email: mailConfig.from_email,
        from_name: mailConfig.from_name,
      });
      setSuccessMsg("மின்னஞ்சல் அமைப்புகள் வெற்றிகரமாக சேமிக்கப்பட்டன!");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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
        officer_id: officerId,
      });
      setSendResult(res);
      setSuccessMsg(res.message || "மின்னஞ்சல் வெற்றிகரமாக அனுப்பப்பட்டது!");
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
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="module-title tamil-text">மின்னஞ்சல் மையம் (Email & Official Mail Hub)</h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
            மனுதாரர் மின்னஞ்சல்களை உட்கொள்ளுதல், அரசு அஞ்சல் சர்வர் இணைப்பு சோதனை & அதிகாரப்பூர்வ ஒப்புகை கடிதம் அனுப்புதல்
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={loadInbox} disabled={loading} title="அஞ்சல்களை புதுப்பி">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span className="tamil-text">புதுப்பி</span>
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div style={{ padding: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 8, fontSize: '0.85rem', display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div style={{ padding: 12, background: '#dcfce7', color: '#166534', borderRadius: 8, fontSize: '0.85rem', display: 'flex', gap: 8, alignItems: 'center' }}>
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
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
        <button
          className={`tab tamil-text ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Server size={14} style={{ display: 'inline', marginRight: 6 }} />
          சர்வர் இணைப்பு & சோதனை (Connection Test)
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
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontSize: '0.7rem', fontWeight: 600 }}>
                        <Paperclip size={10} />
                        இணைப்புகள் ({eml.attachments?.length || 1})
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', display: 'flex', gap: 12 }}>
                    <span><strong>அனுப்பியவர்:</strong> {eml.sender}</span>
                    <span><strong>தேதி:</strong> {eml.date}</span>
                  </div>

                  <p className="tamil-text" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginTop: 4, lineHeight: 1.5 }}>
                    {eml.snippet}...
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 160 }}>
                  <button
                    className="btn btn-primary btn-sm tamil-text"
                    onClick={() => handleIngestEmail(eml.uid)}
                    disabled={ingestingUid === eml.uid}
                    style={{ gap: 6 }}
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
        <div className="card" style={{ padding: 24 }}>
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
                <th>தேதி & நேரம்</th>
                <th>பெறுநர் (Recipient)</th>
                <th>தலைப்பு (Subject)</th>
                <th>அலுவலர்</th>
                <th>நிலை (Status)</th>
              </tr>
            </thead>
            <tbody>
              {sentLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--color-text-muted)' }}>
                    அனுப்பப்பட்ட மின்னஞ்சல்கள் பதிவு ஏதுமில்லை.
                  </td>
                </tr>
              ) : (
                sentLogs.map((log, i) => (
                  <tr key={log.email_id || i}>
                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                      {log.sent_at}
                    </td>
                    <td style={{ fontWeight: 600 }}>{log.recipient_email}</td>
                    <td className="tamil-text">{log.subject}</td>
                    <td>{log.officer_id}</td>
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

      {/* ─── TAB 4: SERVER CONNECTION & TEST ─────────────────────────────── */}
      {activeTab === 'settings' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Presets */}
          <div className="card" style={{ padding: 18 }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 8 }}>
              விரைவு சேவையக முன்னமைப்புகள் (Quick Mail Presets):
            </label>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {Object.entries(PRESETS).map(([k, p]) => (
                <button
                  key={k}
                  className="btn btn-ghost btn-sm"
                  onClick={() => handleApplyPreset(k)}
                  style={{ border: '1px solid var(--color-surface-border)' }}
                >
                  <span>{p.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Connection Test Diagnostics Banner */}
          {testResults && (
            <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {/* IMAP Result */}
              <div className="card" style={{
                borderLeft: `4px solid ${testResults.imap.status === 'success' ? 'var(--color-tn-success)' : 'var(--color-tn-danger)'}`,
                padding: 16,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>📡 IMAP உள்வரும் இணைப்பு (Inbound)</span>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    background: testResults.imap.status === 'success' ? '#dcfce7' : '#fee2e2',
                    color: testResults.imap.status === 'success' ? '#166534' : '#991b1b',
                  }}>
                    {testResults.imap.status === 'success' ? '🟢 வெற்றியடைந்தது' : '🔴 தோல்வி'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: 8, color: 'var(--color-text-secondary)' }}>
                  சர்வர்: <code>{testResults.imap.server}:{testResults.imap.port}</code>
                </div>
                <p className="tamil-text" style={{ fontSize: '0.85rem', marginTop: 6, fontWeight: 600 }}>
                  {testResults.imap.message}
                </p>
              </div>

              {/* SMTP Result */}
              <div className="card" style={{
                borderLeft: `4px solid ${testResults.smtp.status === 'success' ? 'var(--color-tn-success)' : 'var(--color-tn-danger)'}`,
                padding: 16,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>📤 SMTP வெளிச்செல்லும் இணைப்பு (Outbound)</span>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    background: testResults.smtp.status === 'success' ? '#dcfce7' : '#fee2e2',
                    color: testResults.smtp.status === 'success' ? '#166534' : '#991b1b',
                  }}>
                    {testResults.smtp.status === 'success' ? '🟢 வெற்றியடைந்தது' : '🔴 தோல்வி'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: 8, color: 'var(--color-text-secondary)' }}>
                  சர்வர்: <code>{testResults.smtp.server}:{testResults.smtp.port}</code>
                </div>
                <p className="tamil-text" style={{ fontSize: '0.85rem', marginTop: 6, fontWeight: 600 }}>
                  {testResults.smtp.message}
                </p>
              </div>
            </div>
          )}

          {/* Configuration Form */}
          <div className="card" style={{ padding: 24 }}>
            <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    IMAP Server (உள்வரும் சர்வர்)
                  </label>
                  <input
                    type="text"
                    value={mailConfig.imap_server}
                    onChange={(e) => setMailConfig({ ...mailConfig, imap_server: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    IMAP Port
                  </label>
                  <input
                    type="number"
                    value={mailConfig.imap_port}
                    onChange={(e) => setMailConfig({ ...mailConfig, imap_port: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    SMTP Server (வெளிச்செல்லும் சர்வர்)
                  </label>
                  <input
                    type="text"
                    value={mailConfig.smtp_server}
                    onChange={(e) => setMailConfig({ ...mailConfig, smtp_server: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    SMTP Port
                  </label>
                  <input
                    type="number"
                    value={mailConfig.smtp_port}
                    onChange={(e) => setMailConfig({ ...mailConfig, smtp_port: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    மின்னஞ்சல் முகவரி (Email / Username)
                  </label>
                  <input
                    type="text"
                    value={mailConfig.imap_user}
                    placeholder="officer@erode.tn.gov.in"
                    onChange={(e) => setMailConfig({ ...mailConfig, imap_user: e.target.value, smtp_user: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                    கடவுச்சொல் / App Password
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    value={mailConfig.imap_password}
                    onChange={(e) => setMailConfig({ ...mailConfig, imap_password: e.target.value, smtp_password: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--color-surface-border)', background: 'var(--color-surface-input)', color: 'var(--color-text-primary)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                  style={{ gap: 8 }}
                >
                  <RefreshCw size={14} className={testingConnection ? 'animate-spin' : ''} />
                  <span className="tamil-text">{testingConnection ? 'இணைப்பை சோதிக்கிறது...' : '🔗 இணைப்பைச் சோதி (Test Live Connection)'}</span>
                </button>

                <button type="submit" className="btn btn-primary" disabled={loading}>
                  <Save size={16} />
                  <span className="tamil-text">{loading ? 'சேமிக்கிறது...' : 'அமைப்புகளை சேமி'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
