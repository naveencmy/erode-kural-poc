import React, { useState, useRef } from 'react';
import useAppStore from '../../stores/appStore';
import { generateContent, exportContentDocx } from '../../lib/api';
import html2pdf from 'html2pdf.js';
import {
  Stamp, Sparkles, FileCheck, Download, FileText, ChevronRight,
  Newspaper, Bell, FileText as FileTextIcon, ClipboardList, RefreshCw,
  Copy, CheckCheck, Pencil, Save, X, ChevronDown, ChevronUp, SlidersHorizontal, Plus,
} from 'lucide-react';

// ─── Template definitions ─────────────────────────────────────────────────────
const TEMPLATES = [
  {
    id: 'press_release',
    titleEn: 'Press Release',
    titleTa: 'செய்தி குறிப்பு',
    descTa: 'மாவட்ட ஆட்சியர் அலுவலக அதிகாரப்பூர்வ செய்தி வெளியீடு',
    icon: Newspaper,
    color: '#3b82f6',
    placeholder: 'எ.கா: ஜல் ஜீவன் திட்டம் — ஈரோடு மாவட்டத்தில் 1200 வீடுகளுக்கு குடிநீர் இணைப்பு வழங்கல்',
    detailPlaceholder: 'திட்டத்தின் நோக்கம், பயனடைந்த கிராமங்கள், பயனாளிகள் எண்ணிக்கை, நிதி ஒதுக்கீடு விவரங்கள்...',
  },
  {
    id: 'circular',
    titleEn: 'Official Circular',
    titleTa: 'அலுவலக சுற்றறிக்கை',
    descTa: 'துறை சார்ந்த அனைத்து அலுவலர்களுக்கான சுற்றறிக்கை',
    icon: Bell,
    color: '#f59e0b',
    placeholder: 'எ.கா: கோடை விடுமுறை காலத்தில் அலுவலக நேரம் மாற்றம்',
    detailPlaceholder: 'மாற்றத்தின் காரணம், அமல்படுத்தும் தேதி, பாதிக்கப்படும் துறைகள்...',
  },
  {
    id: 'memo',
    titleEn: 'Office Memorandum',
    titleTa: 'அலுவலக குறிப்பாணை',
    descTa: 'உள் விவகாரங்கள் மற்றும் ஒழுங்குமுறை உத்தரவுகள்',
    icon: FileTextIcon,
    color: '#8b5cf6',
    placeholder: 'எ.கா: வருவாய் துறை — பட்டா மாறுதல் கோப்புகள் தீர்வு காணாத பட்டியல்',
    detailPlaceholder: 'தீர்வு காணாத கோப்புகளின் விவரம், காரண விளக்கம், எடுக்க வேண்டிய நடவடிக்கை...',
  },
  {
    id: 'meeting_minutes',
    titleEn: 'Meeting Minutes',
    titleTa: 'கூட்ட நடவடிக்கை பதிவேடு',
    descTa: 'திங்கள் மக்கள் குறைதீர்க்கும் நாள் கூட்ட விவரம்',
    icon: ClipboardList,
    color: '#10b981',
    placeholder: 'எ.கா: திங்கள் மக்கள் குறைதீர்க்கும் கூட்டம் — ஆகஸ்ட் 2026 மூன்றாவது வாரம்',
    detailPlaceholder: '1. கலந்துகொண்ட அலுவலர்கள்\n2. மனுக்களின் எண்ணிக்கை\n3. தீர்வு காணப்பட்ட மனுக்கள்\n4. அடுத்த நடவடிக்கை',
  },
];

// ─── Source badge ─────────────────────────────────────────────────────────────
function SourceBadge({ source }) {
  const isAI = source === 'ollama';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 10px', borderRadius: 20, fontSize: '0.7rem', fontWeight: 700,
      background: isAI ? 'rgba(59,130,246,0.15)' : 'rgba(107,114,128,0.15)',
      color: isAI ? '#60a5fa' : '#9ca3af',
      border: `1px solid ${isAI ? 'rgba(59,130,246,0.3)' : 'rgba(107,114,128,0.3)'}`,
    }}>
      <Sparkles size={10} />
      {isAI ? 'AI Enhanced' : 'Template'}
    </span>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function ContentModule() {
  const { officerId } = useAppStore();
  const [selectedTemplate, setSelectedTemplate] = useState(TEMPLATES[0].id);
  const activeTmpl = TEMPLATES.find(t => t.id === selectedTemplate) || TEMPLATES[0];

  const [subject, setSubject] = useState('');
  const [details, setDetails] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');

  const resultRef = useRef(null);
  const [isFormOpen, setIsFormOpen] = useState(true);
  const formRef = useRef(null);

  async function handleGenerate(e) {
    e.preventDefault();
    if (!subject.trim()) return;
    setLoading(true);
    setError(null);
    setIsEditing(false);
    try {
      const res = await generateContent(selectedTemplate, { subject, details }, officerId);
      setResult(res);
      setEditedText(res.generated_text);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      setError(err.message || 'உள்ளடக்கம் உருவாக்குவதில் பிழை ஏற்பட்டது.');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      await exportContentDocx(result.content_id, result.ref_number, result.template_type, editedText);
    } catch (err) {
      alert('DOCX export failed: ' + err.message);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportPdf() {
    setExportingPdf(true);
    try {
      const filename = `${result.ref_number.replace(/\//g, '_')}_${result.template_type}.pdf`;

      // Parse editedText into structured body paragraphs safely
      const rawParas = editedText.split('\n\n').map(p => p.trim()).filter(Boolean);
      const cleanBodyParas = [];

      for (const p of rawParas) {
        const isShort = p.length < 110;
        if (isShort && (
          p.startsWith('செ.வெ.எண்') ||
          p.startsWith('சுற்றறிக்கை எண்') ||
          p.startsWith('குறிப்பாணை எண்') ||
          p.startsWith('எண்:') ||
          p.startsWith('நாள்') ||
          p === '----' || p === '---' || p.startsWith('----------------') || p.startsWith('========') ||
          p === 'அவர்களின் செய்திக்குறிப்பு-' ||
          p === 'அவர்களின் சுற்றறிக்கை-' ||
          p === 'அவர்களின் அலுவலகக் குறிப்பாணை-' ||
          p === 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,' ||
          p === 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,\nஅவர்களின் செய்திக்குறிப்பு-' ||
          p.startsWith('வெளியீடு செய்தி மக்கள் தொடர்பு அலுவலர்') ||
          p.startsWith('வெளியீடு - செய்தி மக்கள் தொடர்பு அலுவலர்')
        )) {
          continue;
        }
        cleanBodyParas.push(p);
      }

      let refLabel = `செ.வெ.எண் - ${result.ref_number}`;
      let titleType = 'அவர்களின் செய்திக்குறிப்பு-';

      if (result.template_type === 'circular') {
        refLabel = `சுற்றறிக்கை எண் - ${result.ref_number}`;
        titleType = 'அவர்களின் சுற்றறிக்கை-';
      } else if (result.template_type === 'memo') {
        refLabel = `குறிப்பாணை எண் - ${result.ref_number}`;
        titleType = 'அவர்களின் அலுவலகக் குறிப்பாணை-';
      }

      // Build styled HTML matching authentic original Erode District document with crisp page breaks
      const container = document.createElement('div');
      container.style.width = '700px';
      container.style.padding = '20px 25px';
      container.style.background = '#ffffff';
      container.style.color = '#000000';
      container.style.fontFamily = "'Nirmala UI', 'Noto Sans Tamil', 'Latha', Arial, sans-serif";
      container.style.boxSizing = 'border-box';

      if (result.template_type === 'meeting_minutes') {
        const cleanMinutesParas = rawParas.filter(p => {
          const isShort = p.length < 110;
          if (isShort && (
            p.includes('கூட்ட நடவடிக்கைகள்') && p.includes('தலைமையில்') ||
            p.includes('முன்னிலை:') ||
            p.startsWith('எண்:') ||
            p.startsWith('பொருள்:') ||
            p.startsWith('பார்வை:') ||
            p === '<><><>' ||
            p.includes('ஓம்/-ச.கந்தசாமி') ||
            p.includes('நேர்முக உதவியாளர்') ||
            p.startsWith('----------------')
          )) {
            return false;
          }
          return true;
        });

        container.innerHTML = `
          <div style="page-break-inside: avoid; break-inside: avoid;">
            <div style="text-align: center; font-weight: bold; font-size: 12pt; color: #000000; line-height: 1.45; margin-bottom: 12px;">
              ஈரோடு மாவட்ட ஆட்சித்தலைவர் அவர்கள் தலைமையில் ${result.date_display} அன்று<br/>
              நடைபெற்ற ${result.subject} கூட்ட நடவடிக்கைகள்<br/>
              <span style="font-size: 11pt;">முன்னிலை: திரு.ச.கந்தசாமி, இ.ஆ.ப.,</span>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: bold; font-size: 10.5pt; color: #000000; margin-bottom: 10px; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 6px 0;">
              <span>எண்: வே/${result.ref_number}/2026</span>
              <span>நாள்: ${result.date_display}</span>
            </div>

            <div style="font-size: 10.5pt; color: #000000; margin-bottom: 14px; line-height: 1.5;">
              <div style="font-weight: bold;">பொருள்: ${result.subject} – கூட்ட நடவடிக்கைகள் – ஒப்புதல் அளித்தல் – தொடர்பாக.</div>
              <div style="color: #222; margin-top: 4px;">பார்வை: அரசாணை எண்: 78 வேளாண்மை (வே.உ.6) துறை, நாள்: 17.02.2016.</div>
              <div style="text-align: center; font-weight: bold; letter-spacing: 2px; margin-top: 6px;">&lt;&gt;&lt;&gt;&lt;&gt;</div>
            </div>
          </div>

          <div style="color: #000000; font-size: 10.5pt; line-height: 1.75;">
            ${cleanMinutesParas.map(p => `
              <div style="page-break-inside: avoid; break-inside: avoid; margin-bottom: 14px; text-align: justify; text-justify: inter-word; color: #000000; font-size: 10.5pt; line-height: 1.75;">
                ${p.replace(/\n/g, '<br/>')}
              </div>
            `).join('')}
          </div>

          <div style="page-break-inside: avoid; break-inside: avoid; margin-top: 25px;">
            <div style="display: flex; justify-content: flex-end; text-align: right; font-weight: bold; font-size: 10.5pt; color: #000000; margin-bottom: 15px;">
              <div>
                ஓம்/-ச.கந்தசாமி<br/>
                மாவட்ட ஆட்சித்தலைவர்,<br/>
                ஈரோடு.
              </div>
            </div>
            <div style="text-align: center; font-size: 10pt; color: #333333; line-height: 1.5;">
              <div>/உத்தரவுப்படி/</div>
              <div style="margin-top: 10px; font-weight: bold;">நேர்முக உதவியாளர், மாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.</div>
            </div>
          </div>
        `;
      } else {
        container.innerHTML = `
          <div style="page-break-inside: avoid; break-inside: avoid;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: bold; font-size: 11pt; color: #000000; margin-bottom: 20px;">
              <span>${refLabel}</span>
              <span>நாள் - ${result.date_display}</span>
            </div>

            <div style="text-align: center; margin-bottom: 22px;">
              <div style="font-weight: bold; font-size: 13pt; color: #000000; line-height: 1.45;">
                ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,<br/>
                ${titleType}
              </div>
              <div style="font-weight: bold; color: #000000; letter-spacing: 2px; margin-top: 6px;">----</div>
            </div>
          </div>

          <div style="color: #000000; font-size: 11pt; line-height: 1.8;">
            ${cleanBodyParas.map(p => `
              <div style="page-break-inside: avoid; break-inside: avoid; margin-bottom: 14px; text-align: justify; text-justify: inter-word; color: #000000; font-size: 11pt; line-height: 1.8;">
                ${p.replace(/\n/g, '<br/>')}
              </div>
            `).join('')}
          </div>

          <div style="page-break-inside: avoid; break-inside: avoid; margin-top: 25px; border-top: 1.5px solid #000000; padding-top: 10px;">
            <div style="font-weight: bold; font-size: 10.5pt; color: #000000;">வெளியீடு செய்தி மக்கள் தொடர்பு அலுவலர், ஈரோடு மாவட்டம்.</div>
          </div>
        `;
      }

      const opt = {
        margin: [12, 12, 12, 12],
        filename: filename,
        image: { type: 'jpeg', quality: 1.0 },
        html2canvas: { 
          scale: 2.5, 
          useCORS: true, 
          letterRendering: true, 
          backgroundColor: '#ffffff',
          scrollY: 0,
          windowWidth: 700
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      };

      await html2pdf().set(opt).from(container).save();
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('PDF export failed: ' + err.message);
    } finally {
      setExportingPdf(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(editedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleStartEdit() {
    setIsEditing(true);
  }

  function handleSaveEdit() {
    setResult(prev => ({ ...prev, generated_text: editedText }));
    setIsEditing(false);
  }

  function handleCancelEdit() {
    setEditedText(result.generated_text);
    setIsEditing(false);
  }

  function handleReset() {
    setResult(null);
    setError(null);
    setSubject('');
    setDetails('');
    setIsEditing(false);
    setEditedText('');
    setIsFormOpen(true);
  }

  function scrollToForm() {
    setIsFormOpen(true);
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 16 }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Stamp size={20} style={{ color: 'var(--color-tn-accent)' }} />
          <span className="tamil-text" style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--color-text-primary)' }}>
            அதிகாரப்பூர்வ உள்ளடக்க ஜெனரேட்டர்
          </span>
        </div>
      </div>

      {/* ── Template Selector ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
        {TEMPLATES.map((tmpl) => {
          const Icon = tmpl.icon;
          const isActive = selectedTemplate === tmpl.id;
          return (
            <button
              key={tmpl.id}
              onClick={() => { setSelectedTemplate(tmpl.id); setIsFormOpen(true); }}
              style={{
                cursor: 'pointer', textAlign: 'left', padding: '8px 12px',
                borderRadius: 10, border: `2px solid ${isActive ? tmpl.color : 'var(--color-surface-border)'}`,
                background: isActive ? `${tmpl.color}18` : 'var(--color-surface-card)',
                transition: 'all 0.2s', outline: 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Icon size={14} style={{ color: tmpl.color }} />
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                    {tmpl.titleEn}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: tmpl.color, fontWeight: 600 }} className="tamil-text">
                    {tmpl.titleTa}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* ── Input Form (Always available to view & tweak) ── */}
      <div ref={formRef} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 16px', transition: 'all 0.3s' }}>
        <div
          onClick={() => result && setIsFormOpen(!isFormOpen)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            paddingBottom: isFormOpen ? 8 : 0,
            borderBottom: isFormOpen ? '1px solid var(--color-surface-border)' : 'none',
            cursor: result ? 'pointer' : 'default',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {React.createElement(activeTmpl.icon, { size: 16, style: { color: activeTmpl.color } })}
            <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)' }} className="tamil-text">
              {activeTmpl.titleTa} ({activeTmpl.titleEn}) — உள்ளீடுகள் & குறிப்புகள்
            </span>
            {result && (
              <span style={{
                padding: '2px 8px', borderRadius: 12, fontSize: '0.68rem', fontWeight: 600,
                background: 'rgba(59,130,246,0.12)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.25)',
              }}>
                {isFormOpen ? 'Click to minimize' : 'Click to view & edit inputs'}
              </span>
            )}
          </div>
          {result && (
            <div style={{ color: 'var(--color-text-secondary)' }}>
              {isFormOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          )}
        </div>

        {isFormOpen && (
          <form onSubmit={handleGenerate} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 600, display: 'block', marginBottom: 4, color: 'var(--color-text-primary)' }}>
                பொருள் (Subject) <span style={{ color: activeTmpl.color }}>*</span>
              </label>
              <textarea
                rows={2}
                placeholder={activeTmpl.placeholder}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
                className="tamil-text"
                style={{
                  width: '100%', padding: '10px 14px', borderRadius: 8,
                  border: `1px solid ${subject ? activeTmpl.color + '80' : 'var(--color-surface-border)'}`,
                  background: 'var(--color-surface-input)', color: 'var(--color-text-primary)',
                  outline: 'none', fontSize: '1rem', transition: 'border-color 0.2s',
                  lineHeight: '1.5', resize: 'vertical', minHeight: '52px',
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}
              />
            </div>

            <div>
              <label className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 600, display: 'block', marginBottom: 4, color: 'var(--color-text-primary)' }}>
                முக்கிய குறிப்புகள் / Key Points & Context
              </label>
              <textarea
                rows={5}
                placeholder={activeTmpl.detailPlaceholder}
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%', padding: '10px 14px', borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)', color: 'var(--color-text-primary)',
                  outline: 'none', resize: 'vertical', fontSize: '1rem',
                  fontFamily: 'inherit', lineHeight: 1.6,
                }}
              />
            </div>

            {error && (
              <div style={{
                padding: '10px 14px', borderRadius: 8, fontSize: '0.82rem',
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                color: '#f87171',
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!subject.trim() || loading}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start',
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: loading || !subject.trim()
                  ? 'var(--color-surface-border)'
                  : `linear-gradient(135deg, ${activeTmpl.color}, ${activeTmpl.color}bb)`,
                color: '#fff', fontWeight: 700, fontSize: '1rem',
                cursor: loading || !subject.trim() ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {loading ? (
                <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> உருவாக்குகிறது...</>
              ) : result ? (
                <><RefreshCw size={15} /> மீண்டும் உருவாக்கு (Regenerate)</>
              ) : (
                'ஆவணம் உருவாக்கு'
              )}
            </button>
          </form>
        )}
      </div>

      {/* ── Result ── */}
      {result && (
        <div ref={resultRef} style={{ display: 'flex', flexDirection: 'column', gap: 8, animation: 'fadeIn 0.4s ease' }}>

          {/* Result action bar */}
          <div className="card" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
            background: `linear-gradient(135deg, ${activeTmpl.color}15, var(--color-surface-card))`,
            border: `1px solid ${activeTmpl.color}40`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <FileCheck size={20} style={{ color: activeTmpl.color }} />
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--color-text-primary)' }} className="tamil-text">
                  வெற்றிகரமாக உருவாக்கப்பட்டது!
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', display: 'flex', gap: 8, alignItems: 'center', marginTop: 2 }}>
                  <span style={{ fontWeight: 600, color: activeTmpl.color }}>{result.ref_number}</span>
                  <span>·</span>
                  <span>{result.date_display}</span>
                  <span>·</span>
                  <SourceBadge source={result.source} />
                  {isEditing && (
                    <span style={{
                      padding: '1px 8px', borderRadius: 10, fontSize: '0.68rem', fontWeight: 700,
                      background: 'rgba(251,191,36,0.2)', color: '#fbbf24',
                      border: '1px solid rgba(251,191,36,0.4)',
                    }}>
                      ✎ Editing
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {/* Edit / Save / Cancel */}
              {!isEditing ? (
                <button onClick={handleStartEdit} style={btnStyle('#fbbf24')} title="Edit the generated draft directly">
                  <Pencil size={13} /> Edit
                </button>
              ) : (
                <>
                  <button onClick={handleSaveEdit} style={btnStyle('#10b981')}>
                    <Save size={13} /> Save
                  </button>
                  <button onClick={handleCancelEdit} style={btnStyle('#ef4444')}>
                    <X size={13} /> Cancel
                  </button>
                </>
              )}

              {/* Copy */}
              <button onClick={handleCopy} style={btnStyle()} title="Copy text to clipboard">
                {copied ? <><CheckCheck size={13} /> Copied!</> : <><Copy size={13} /> Copy</>}
              </button>

              {/* PDF */}
              <button
                onClick={handleExportPdf}
                disabled={exportingPdf || isEditing}
                style={{ ...btnStyle(), opacity: isEditing ? 0.5 : 1 }}
                title="Download as PDF file (.pdf)"
              >
                {exportingPdf ? (
                  <><RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> Exporting...</>
                ) : (
                  <><Download size={13} /> PDF</>
                )}
              </button>

              {/* DOCX */}
              <button onClick={handleExport} disabled={exporting || isEditing} style={{
                ...btnStyle(activeTmpl.color, true),
                opacity: isEditing ? 0.5 : 1,
              }} title="Download as Microsoft Word document (.docx)">
                {exporting
                  ? <><RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> Exporting...</>
                  : <><Download size={13} /> DOCX</>}
              </button>

              {/* New document */}
              <button onClick={handleReset} style={btnStyle()} title="Start a fresh new document">
                <Plus size={13} /> New Document
              </button>
            </div>
          </div>

          {/* Generated text — view OR edit */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{
              padding: '10px 16px', borderBottom: '1px solid var(--color-surface-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'var(--color-surface-hover)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileText size={14} style={{ color: 'var(--color-text-secondary)' }} />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                  {isEditing ? '✎ Edit Document Draft' : 'Document Preview'}
                </span>
              </div>
            </div>

            {isEditing ? (
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%', minHeight: 480,
                  padding: '16px 20px', margin: 0, border: 'none',
                  fontFamily: "'Nirmala UI', 'Noto Sans Tamil', monospace",
                  fontSize: '1rem', lineHeight: 1.8, resize: 'vertical',
                  background: 'var(--color-surface-input)', color: 'var(--color-text-primary)',
                  outline: 'none',
                }}
              />
            ) : (
              <pre className="tamil-text" style={{
                padding: '16px 20px', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                fontFamily: "'Nirmala UI', 'Noto Sans Tamil', monospace",
                fontSize: '1rem', lineHeight: 1.8,
                color: 'var(--color-text-primary)',
                maxHeight: 480, overflowY: 'auto',
              }}>
                {editedText}
              </pre>
            )}
          </div>

          {/* Save reminder when editing */}
          {isEditing && (
            <div style={{
              padding: '10px 16px', borderRadius: 8, fontSize: '0.8rem',
              background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.25)',
              color: '#fbbf24', display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <Pencil size={13} />
              நீங்கள் ஆவணத்தை திருத்துகிறீர்கள். மாற்றங்களை சேமிக்க <strong>Save</strong> அழுத்தவும்.
              DOCX download only works after saving edits.
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}

// ─── Button style helper ──────────────────────────────────────────────────────
function btnStyle(color, filled = false) {
  return {
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '8px 14px', borderRadius: 7, cursor: 'pointer',
    fontSize: '0.88rem', fontWeight: filled ? 700 : 500,
    border: filled ? 'none' : '1px solid var(--color-surface-border)',
    background: filled ? color : 'var(--color-surface-hover)',
    color: filled ? '#fff' : (color || 'var(--color-text-primary)'),
    transition: 'opacity 0.15s',
  };
}
