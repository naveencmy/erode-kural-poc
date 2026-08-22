import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import {
  fetchBulkItemDetail,
  approveItem,
  editDraft,
  generateFileNumber,
  exportDocx,
  sendOfficialEmail,
} from '../../lib/api';
import { formatDate, getStatusLabel, getPriorityLabel, downloadBlob } from '../../lib/utils';
import ConfidenceBadge from '../shared/ConfidenceBadge';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Download,
  Hash,
  Edit3,
  Save,
  Shield,
  FileText,
  Tag,
  FileCheck,
  Search,
  Mail,
  Send,
  X,
  AlertCircle,
  Check,
} from 'lucide-react';

const TABS = ['tab_ocr', 'tab_entities', 'tab_classification', 'tab_draft', 'tab_grounding'];

export default function BulkDetailView({ sourceId, onBack, onRefresh }) {
  const { t } = useTranslation();
  const { officerId, openInspector } = useAppStore();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('tab_ocr');
  const [editMode, setEditMode] = useState(false);
  const [draftText, setDraftText] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [fileNumber, setFileNumber] = useState(null);

  // Send Mail Modal State
  const [showMailModal, setShowMailModal] = useState(false);
  const [mailRecipient, setMailRecipient] = useState('');
  const [mailSubject, setMailSubject] = useState('');
  const [mailBody, setMailBody] = useState('');
  const [mailSending, setMailSending] = useState(false);
  const [mailStatusMsg, setMailStatusMsg] = useState(null);

  useEffect(() => {
    loadDetail();
  }, [sourceId]);

  const loadDetail = async () => {
    setLoading(true);
    try {
      const data = await fetchBulkItemDetail(sourceId);
      setDetail(data);
      if (data.draft?.draft_text) {
        setDraftText(data.draft.draft_text);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (action) => {
    setActionLoading(true);
    try {
      await approveItem(sourceId, officerId, action);
      await loadDetail();
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    setActionLoading(true);
    try {
      await editDraft(sourceId, officerId, draftText);
      setEditMode(false);
      await loadDetail();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerateFileNo = async () => {
    setActionLoading(true);
    try {
      const dept = detail?.classification?.department || 'பொது_வழக்கு';
      const result = await generateFileNumber(sourceId, dept, officerId);
      setFileNumber(result.file_number);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExportDocx = async () => {
    setActionLoading(true);
    try {
      const blob = await exportDocx(sourceId);
      downloadBlob(blob, `Ack_${sourceId.slice(0, 8)}.docx`);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenMailModal = () => {
    // Auto-detect email from extracted entities if available
    const foundEmail = detail?.entities?.find(
      (e) => e.entity_type?.toLowerCase() === 'email' || (e.entity_value && e.entity_value.includes('@'))
    );
    setMailRecipient(foundEmail?.entity_value || '');
    setMailSubject(
      `ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம் - மனு ஒப்புகை / ஆணை (${fileNumber || sourceId.slice(0, 10)})`
    );
    setMailBody(draftText || detail?.draft?.draft_text || '');
    setMailStatusMsg(null);
    setShowMailModal(true);
  };

  const handleSendMail = async (e) => {
    e?.preventDefault();
    if (!mailRecipient || !mailRecipient.includes('@')) {
      setMailStatusMsg({ type: 'error', text: 'செல்லுபடியாகும் பெறுநர் மின்னஞ்சல் முகவரி தேவை (Valid email required)' });
      return;
    }
    setMailSending(true);
    setMailStatusMsg(null);
    try {
      const res = await sendOfficialEmail({
        recipient_email: mailRecipient,
        subject: mailSubject,
        body: mailBody,
        officer_id: officerId,
        source_id: sourceId,
      });
      setMailStatusMsg({
        type: 'success',
        text: res.message || 'அதிகாரப்பூர்வ மின்னஞ்சல் வெற்றிகரமாக அனுப்பப்பட்டது!',
      });
      setTimeout(() => {
        setShowMailModal(false);
        setMailStatusMsg(null);
      }, 2000);
    } catch (err) {
      setMailStatusMsg({ type: 'error', text: err.message || 'மின்னஞ்சல் அனுப்புதல் தோல்வி' });
    } finally {
      setMailSending(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <div className="spinner" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: 'var(--color-tn-danger)' }}>{error || 'Not found'}</p>
        <button className="btn btn-ghost" onClick={onBack} style={{ marginTop: 16 }}>
          <ArrowLeft size={16} /> {t('detail.back_to_list')}
        </button>
      </div>
    );
  }

  const { ocr_pages = [], entities = [], classification, draft } = detail;
  const groundingMap = draft?.grounding_map || {};

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <button className="btn btn-ghost btn-sm" onClick={onBack}>
          <ArrowLeft size={16} />
          <span className="tamil-text">{t('detail.back_to_list')}</span>
        </button>
        <div style={{ flex: 1 }}>
          <h2 className="module-title" style={{ fontSize: '1.05rem', fontWeight: 700 }}>
            {detail.file_name}
          </h2>
          <div style={{ display: 'flex', gap: 8, marginTop: 4, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={`status-badge status-${detail.status}`}>{getStatusLabel(detail.status)}</span>
            <span style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)' }}>
              {detail.source_type === 'email' ? '📧' : '📄'} {detail.source_id?.slice(0, 12)}…
            </span>
            <span style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)' }}>
              {formatDate(detail.received_at)}
            </span>
            {fileNumber && (
              <span style={{
                padding: '2px 10px',
                background: 'var(--color-tn-accent)',
                color: 'var(--color-tn-primary-dark)',
                borderRadius: 4,
                fontSize: '0.88rem',
                fontWeight: 700,
              }}>
                📁 {fileNumber}
              </span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-ghost btn-sm" onClick={handleGenerateFileNo} disabled={actionLoading} title={t('bulk.generate_file_no')} style={{ fontSize: '0.88rem' }}>
            <Hash size={14} />
          </button>
          <button className="btn btn-ghost btn-sm" onClick={handleExportDocx} disabled={actionLoading} title={t('bulk.export_docx')} style={{ fontSize: '0.88rem' }}>
            <Download size={14} />
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleOpenMailModal}
            disabled={actionLoading}
            title={t('bulk.send_mail')}
            style={{ fontSize: '0.88rem', color: 'var(--color-tn-primary)', borderColor: 'var(--color-tn-accent)' }}
          >
            <Mail size={14} />
            <span className="tamil-text">{t('bulk.send_mail')}</span>
          </button>
          <button
            className="btn btn-success btn-sm"
            onClick={() => handleApprove('approve')}
            disabled={actionLoading || draft?.officer_approved}
            style={{ fontSize: '0.88rem' }}
          >
            <CheckCircle2 size={14} />
            <span className="tamil-text">{t('bulk.approve')}</span>
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => handleApprove('reject')}
            disabled={actionLoading}
            style={{ fontSize: '0.88rem' }}
          >
            <XCircle size={14} />
            <span className="tamil-text">{t('bulk.reject')}</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`tab tamil-text ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
            style={{ fontSize: '0.88rem' }}
          >
            {t(`detail.${tab}`)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="card animate-fade-in" key={activeTab} style={{ padding: '12px 16px' }}>
        {/* ─── OCR Text ─────────────── */}
        {activeTab === 'tab_ocr' && (
          <div>
            {ocr_pages.length === 0 ? (
              <p className="tamil-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>{t('detail.no_ocr')}</p>
            ) : (
              ocr_pages.map((page, i) => (
                <div key={page.id || i} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <FileText size={16} style={{ color: 'var(--color-text-muted)' }} />
                    <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{t('detail.ocr_page')} {page.page_number}</span>
                    <ConfidenceBadge score={page.avg_confidence || 0} />
                  </div>
                  <pre
                    className="tamil-text"
                    style={{
                      background: 'var(--color-surface-hover)',
                      padding: '12px 16px',
                      borderRadius: 8,
                      fontSize: '1rem',
                      lineHeight: 1.8,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: 400,
                      overflow: 'auto',
                    }}
                  >
                    {page.full_text_corrected || page.full_text}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}

        {/* ─── Entities ─────────────── */}
        {activeTab === 'tab_entities' && (
          <div>
            {entities.length === 0 ? (
              <p className="tamil-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>{t('detail.no_entities')}</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="tamil-text" style={{ fontSize: '0.95rem' }}>{t('detail.entity_type')}</th>
                    <th className="tamil-text" style={{ fontSize: '0.95rem' }}>{t('detail.entity_value')}</th>
                    <th style={{ fontSize: '0.95rem' }}>{t('detail.ocr_confidence')}</th>
                  </tr>
                </thead>
                <tbody>
                  {entities.map((ent, i) => (
                    <tr key={i}>
                      <td style={{ fontSize: '1rem' }}>
                        <span style={{
                          padding: '2px 8px',
                          background: 'var(--color-surface-hover)',
                          borderRadius: 4,
                          fontSize: '0.88rem',
                          fontWeight: 600,
                        }}>
                          {ent.entity_type}
                        </span>
                      </td>
                      <td className="tamil-text" style={{ fontSize: '1rem' }}>{ent.entity_value}</td>
                      <td style={{ fontSize: '1rem' }}>
                        {ent.confidence != null ? (
                          <ConfidenceBadge score={ent.confidence} />
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ─── Classification ─────────── */}
        {activeTab === 'tab_classification' && (
          <div>
            {!classification ? (
              <p className="tamil-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>{t('detail.no_classification')}</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="card" style={{ borderLeft: '4px solid var(--color-tn-primary)', padding: '12px 16px' }}>
                  <Tag size={16} style={{ color: 'var(--color-text-muted)', marginBottom: 8 }} />
                  <div style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                    {t('detail.dept_label')}
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: 4 }} className="tamil-text">
                    {classification.department}
                  </div>
                </div>
                <div className="card" style={{ borderLeft: '4px solid var(--color-tn-warning)', padding: '12px 16px' }}>
                  <Shield size={16} style={{ color: 'var(--color-text-muted)', marginBottom: 8 }} />
                  <div style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                    {t('detail.priority_label')}
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: 4 }} className={`priority-${classification.priority?.toLowerCase()}`}>
                    {getPriorityLabel(classification.priority)}
                  </div>
                </div>
                <div className="card" style={{ gridColumn: '1 / -1', borderLeft: '4px solid var(--color-tn-accent)', padding: '12px 16px' }}>
                  <FileCheck size={16} style={{ color: 'var(--color-text-muted)', marginBottom: 8 }} />
                  <div style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                    {t('detail.decision_label')}
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: 4 }} className="tamil-text">
                    {classification.final_decision || '—'}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── Draft ─────────────── */}
        {activeTab === 'tab_draft' && (
          <div>
            {!draft ? (
              <p className="tamil-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>{t('detail.no_draft')}</p>
            ) : (
              <>
                {/* Hallucination Score */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <span className="tamil-text" style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>
                    {t('detail.hallucination_score')}:
                  </span>
                  <ConfidenceBadge score={1 - (draft.hallucination_score || 0)} />
                  {draft.officer_approved && (
                    <span style={{
                      padding: '2px 10px',
                      background: '#d1fae5',
                      color: '#065f46',
                      borderRadius: 9999,
                      fontSize: '0.88rem',
                      fontWeight: 700,
                    }}>
                      ✓ {t('bulk.approved')}
                    </span>
                  )}
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                    {editMode ? (
                      <>
                        <button className="btn btn-success btn-sm" onClick={handleSaveDraft} disabled={actionLoading} style={{ fontSize: '0.88rem' }}>
                          <Save size={14} />
                          <span className="tamil-text">{t('common.save')}</span>
                        </button>
                        <button className="btn btn-ghost btn-sm" onClick={() => { setEditMode(false); setDraftText(draft.draft_text); }} style={{ fontSize: '0.88rem' }}>
                          <span className="tamil-text">{t('common.cancel')}</span>
                        </button>
                      </>
                    ) : (
                      <button className="btn btn-ghost btn-sm" onClick={() => setEditMode(true)} style={{ fontSize: '0.88rem' }}>
                        <Edit3 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Draft Text */}
                {editMode ? (
                  <textarea
                    value={draftText}
                    onChange={(e) => setDraftText(e.target.value)}
                    className="tamil-text"
                    style={{
                      width: '100%',
                      minHeight: 300,
                      padding: '12px 16px',
                      borderRadius: 8,
                      border: '2px solid var(--color-tn-primary)',
                      background: 'var(--color-surface-input)',
                      color: 'var(--color-text-primary)',
                      fontSize: '1rem',
                      lineHeight: 1.8,
                      resize: 'vertical',
                      fontFamily: "'Noto Sans Tamil', sans-serif",
                    }}
                  />
                ) : (
                  <pre
                    className="tamil-text"
                    style={{
                      background: 'var(--color-surface-hover)',
                      padding: '12px 16px',
                      borderRadius: 8,
                      fontSize: '1rem',
                      lineHeight: 1.8,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {draft.draft_text}
                  </pre>
                )}

                {/* Missing Fields */}
                {draft.missing_fields?.length > 0 && (
                  <div style={{ marginTop: 12, padding: '12px 16px', background: '#fef3c7', borderRadius: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#92400e' }}>
                      ⚠️ Missing Fields: {draft.missing_fields.join(', ')}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ─── Grounding Inspector ─────── */}
        {activeTab === 'tab_grounding' && (
          <div>
            {Object.keys(groundingMap).length === 0 ? (
              <p className="tamil-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>{t('detail.no_grounding')}</p>
            ) : (
              <table className="grounding-table">
                <thead>
                  <tr>
                    <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                      {t('detail.grounding_field')}
                    </th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                      {t('detail.grounding_value')}
                    </th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
                      {t('detail.grounding_source')}
                    </th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>
                      {t('detail.grounding_confidence')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(groundingMap).map(([field, entry]) => (
                    <tr key={field}>
                      <td className="field-name tamil-text" style={{ fontSize: '1rem' }}>{field}</td>
                      <td className="field-value tamil-text" style={{ fontSize: '1rem' }}>
                        {entry.value || <span style={{ color: 'var(--color-tn-danger)' }}>{t('common.no_data')}</span>}
                      </td>
                      <td>
                        <div className="field-value" style={{ fontSize: '0.75rem' }}>
                          {entry.source || '—'}
                        </div>
                        {entry.source_chunk && (
                          <div className="source-chunk tamil-text">
                            «{entry.source_chunk}»
                          </div>
                        )}
                      </td>
                      <td>
                        <ConfidenceBadge score={entry.confidence || 0} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div style={{ marginTop: 16 }}>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => openInspector(groundingMap)}
              >
                <Search size={14} />
                <span className="tamil-text">{t('inspector.title')}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── Send Official Mail Modal ──────────────── */}
      {showMailModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 16,
          }}
          onClick={() => !mailSending && setShowMailModal(false)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: '100%',
              maxWidth: 640,
              maxHeight: '90vh',
              overflowY: 'auto',
              backgroundColor: 'var(--color-surface-card, #1e293b)',
              color: 'var(--color-text-primary, #f1f5f9)',
              border: '1px solid var(--color-surface-border, #334155)',
              borderRadius: 12,
              padding: '24px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, borderBottom: '1px solid var(--color-surface-border, #334155)', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ padding: 8, borderRadius: 8, background: 'rgba(16, 185, 129, 0.15)', color: 'var(--color-tn-success, #22c55e)' }}>
                  <Mail size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary, #f1f5f9)' }} className="tamil-text">
                    அதிகாரப்பூர்வ மின்னஞ்சல் அனுப்புதல்
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted, #94a3b8)' }}>
                    Send Official Email via Brevo Cloud SMTP
                  </span>
                </div>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setShowMailModal(false)}
                disabled={mailSending}
                style={{ padding: 6, color: 'var(--color-text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Status Feedback Banner */}
            {mailStatusMsg && (
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  marginBottom: 16,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  fontSize: '0.92rem',
                  background: mailStatusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: mailStatusMsg.type === 'success' ? '#10b981' : '#ef4444',
                  border: `1px solid ${mailStatusMsg.type === 'success' ? '#10b981' : '#ef4444'}`,
                }}
              >
                {mailStatusMsg.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
                <span className="tamil-text" style={{ fontWeight: 600 }}>{mailStatusMsg.text}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSendMail} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-primary, #f1f5f9)' }} className="tamil-text">
                  பெறுநர் மின்னஞ்சல் (Recipient Email) *
                </label>
                <input
                  type="email"
                  required
                  value={mailRecipient}
                  onChange={(e) => setMailRecipient(e.target.value)}
                  placeholder="applicant@example.com"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    fontSize: '0.95rem',
                    backgroundColor: 'var(--color-surface-bg, #0f172a)',
                    color: 'var(--color-text-primary, #f1f5f9)',
                    border: '1px solid var(--color-surface-border, #334155)',
                    borderRadius: 8,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-primary, #f1f5f9)' }} className="tamil-text">
                  மின்னஞ்சல் தலைப்பு (Subject) *
                </label>
                <input
                  type="text"
                  required
                  value={mailSubject}
                  onChange={(e) => setMailSubject(e.target.value)}
                  placeholder="மின்னஞ்சல் தலைப்பு..."
                  className="tamil-text"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    fontSize: '0.95rem',
                    backgroundColor: 'var(--color-surface-bg, #0f172a)',
                    color: 'var(--color-text-primary, #f1f5f9)',
                    border: '1px solid var(--color-surface-border, #334155)',
                    borderRadius: 8,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-primary, #f1f5f9)' }} className="tamil-text">
                  மின்னஞ்சல் உரை / வரைவு ஆணை (Body) *
                </label>
                <textarea
                  required
                  rows={8}
                  value={mailBody}
                  onChange={(e) => setMailBody(e.target.value)}
                  className="tamil-text"
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    fontSize: '0.95rem',
                    lineHeight: 1.6,
                    resize: 'vertical',
                    backgroundColor: 'var(--color-surface-bg, #0f172a)',
                    color: 'var(--color-text-primary, #f1f5f9)',
                    border: '1px solid var(--color-surface-border, #334155)',
                    borderRadius: 8,
                    outline: 'none',
                  }}
                />
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowMailModal(false)}
                  disabled={mailSending}
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  <span className="tamil-text">{t('common.cancel')}</span>
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={mailSending}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', fontSize: '0.95rem', fontWeight: 600 }}
                >
                  {mailSending ? (
                    <>
                      <div className="spinner" style={{ width: 16, height: 16 }} />
                      <span className="tamil-text">அனுப்பப்படுகிறது...</span>
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      <span className="tamil-text">{t('bulk.send_mail')}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
