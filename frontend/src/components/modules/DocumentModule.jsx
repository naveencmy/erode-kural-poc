import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { uploadDocument } from '../../lib/api';
import { FileText, Upload, CheckCircle2, AlertCircle, Sparkles, FileSpreadsheet } from 'lucide-react';

export default function DocumentModule() {
  const { t } = useTranslation();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [summaryData, setSummaryData] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (e) => {
    const uploadedFile = e.target.files?.[0];
    if (!uploadedFile) return;
    setFile(uploadedFile);
    setLoading(true);
    setError(null);
    try {
      const res = await uploadDocument(uploadedFile);
      setSummaryData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 className="module-title tamil-text">{t('sidebar.document')}</h1>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
          நீண்ட அரசாணை, சுற்றறிக்கை அல்லது மனுக்களை பதிவேற்றி தானியங்கி சுருக்கம் பெறவும்
        </p>
      </div>

      <div
        className="upload-zone"
        onClick={() => document.getElementById('doc-upload-input').click()}
      >
        <input
          id="doc-upload-input"
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={handleUpload}
        />
        <Upload size={36} style={{ color: 'var(--color-text-muted)', marginBottom: 8 }} />
        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }} className="tamil-text">
          {file ? file.name : "ஆவணத்தை பதிவேற்ற கிளிக் செய்யவும் அல்லது இழுத்துவிடவும் (PDF, DOCX, TXT)"}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 4 }} className="tamil-text">
          அதிகபட்ச அளவு: 25 MB
        </div>
      </div>

      {loading && (
        <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 40 }}>
          <div className="spinner" />
          <span className="tamil-text" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
            ஆவணம் பகுப்பாய்வு செய்யப்பட்டு சுருக்கம் தயாரிக்கப்படுகிறது...
          </span>
        </div>
      )}

      {error && (
        <div style={{ padding: 16, background: '#fee2e2', color: '#991b1b', borderRadius: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {summaryData && !loading && (
        <div className="card animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} style={{ color: 'var(--color-tn-accent)' }} />
            <h3 className="tamil-text" style={{ fontSize: '1rem', fontWeight: 700 }}>
              ஆவண சுருக்க நிலை & விபரம்
            </h3>
          </div>
          <div style={{ padding: 16, background: 'var(--color-surface-hover)', borderRadius: 8 }}>
            <p className="tamil-text" style={{ fontSize: '0.9rem', lineHeight: 1.8 }}>
              {summaryData.message || "சுருக்கத் தொகுதி வெற்றிகரமாக இணைக்கப்பட்டுள்ளது."}
            </p>
            <div style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
              கோப்பு: <strong>{summaryData.file_name}</strong> | அடையாளம்: <code>{summaryData.document_id}</code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
