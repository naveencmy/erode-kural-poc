import React, { useState, useRef } from 'react';
import useAppStore from '../../stores/appStore';
import { generateContent, exportContentDocx } from '../../lib/api';
import html2pdf from 'html2pdf.js';
import {
  Stamp, FileCheck, Download, FileText, ChevronRight,
  Newspaper, Bell, FileText as FileTextIcon, ClipboardList, RefreshCw,
  Copy, CheckCheck, ChevronDown, ChevronUp, Plus,
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

  const resultRef = useRef(null);
  const [isFormOpen, setIsFormOpen] = useState(true);
  const formRef = useRef(null);

  async function handleGenerate(e) {
    e.preventDefault();
    if (!subject.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateContent(selectedTemplate, { subject, details, language: 'auto' }, officerId);
      setResult(res);
      setIsFormOpen(false);
    } catch (err) {
      setError(err.message || 'உள்ளடக்கம் உருவாக்குவதில் பிழை ஏற்பட்டது.');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      await exportContentDocx(result.content_id, result.ref_number, result.template_type, result.generated_text);
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

      const rawParas = result.generated_text.split('\n\n').map(p => p.trim()).filter(Boolean);
      const cleanBodyParas = [];

      for (const p of rawParas) {
        const lines = p.split('\n').map(l => l.trim()).filter(Boolean);
        const keptLines = [];
        for (const line of lines) {
          const lineNoNum = line.replace(/^\d+[\.\)]\s*/, '').trim();
          const isShort = lineNoNum.length < 140;

          if (isShort && (
            lineNoNum.startsWith('செ.வெ.எண்') ||
            lineNoNum.startsWith('சுற்றறிக்கை எண்') ||
            lineNoNum.startsWith('குறிப்பாணை எண்') ||
            lineNoNum.startsWith('எண்:') ||
            lineNoNum.startsWith('நாள்') ||
            lineNoNum === '----' || lineNoNum === '---' ||
            lineNoNum.startsWith('----------------') ||
            lineNoNum === 'அவர்களின் செய்திக்குறிப்பு-' ||
            lineNoNum === 'அவர்களின் சுற்றறிக்கை-' ||
            lineNoNum === 'அவர்களின் அலுவலகக் குறிப்பாணை-' ||
            lineNoNum === 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,'
          )) {
            continue;
          }

          if (isShort && (
            lineNoNum.startsWith('வெளியீடு') ||
            lineNoNum.includes('செய்தி மக்கள் தொடர்பு அலுவலர்') ||
            lineNoNum.startsWith('இப்படிக்கு')
          )) {
            continue;
          }

          keptLines.push(line);
        }
        if (keptLines.length > 0) {
          cleanBodyParas.push(keptLines.join('\n'));
        }
      }

      const isEnglishDoc = result.language === 'en';
      const container = document.createElement('div');
      container.style.width = '700px';
      container.style.padding = '20px 25px';
      container.style.background = '#ffffff';
      container.style.color = '#000000';
      container.style.fontFamily = "'Nirmala UI', 'Noto Sans Tamil', 'Latha', Arial, sans-serif";
      container.style.boxSizing = 'border-box';

      let refPrefixLabel = isEnglishDoc ? `PRESS RELEASE NO: ${result.ref_number}` : `செ.வெ.எண் - ${result.ref_number}`;
      let headerTitle = isEnglishDoc
        ? 'PRESS RELEASE ISSUED BY THE DISTRICT COLLECTOR & DISTRICT MAGISTRATE<br/>THIRU S. KANDASAMY, I.A.S., ERODE DISTRICT'
        : 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,<br/>அவர்களின் செய்திக்குறிப்பு-';
      let footerLabel = isEnglishDoc
        ? 'Issued by: District Public Relations Officer, Erode District.'
        : 'வெளியீடு செய்தி மக்கள் தொடர்பு அலுவலர், ஈரோடு மாவட்டம்.';

      if (result.template_type === 'circular') {
        refPrefixLabel = isEnglishDoc ? `CIRCULAR NO: ${result.ref_number}` : `சுற்றறிக்கை எண் - ${result.ref_number}`;
        headerTitle = isEnglishDoc
          ? 'OFFICE OF THE DISTRICT COLLECTOR, ERODE DISTRICT<br/>OFFICIAL CIRCULAR'
          : 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,<br/>அவர்களின் சுற்றறிக்கை-';
        footerLabel = isEnglishDoc
          ? 'By Order of the District Collector, Erode District.'
          : 'மாவட்ட ஆட்சித்தலைவர் அவர்களின் உத்தரவுப்படி, ஈரோடு மாவட்டம்.';
      } else if (result.template_type === 'memo') {
        refPrefixLabel = isEnglishDoc ? `MEMORANDUM NO: ${result.ref_number}` : `குறிப்பாணை எண் - ${result.ref_number}`;
        headerTitle = isEnglishDoc
          ? 'OFFICE OF THE DISTRICT COLLECTOR, ERODE DISTRICT<br/>OFFICE MEMORANDUM'
          : 'ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,<br/>அவர்களின் அலுவலகக் குறிப்பாணை-';
        footerLabel = isEnglishDoc
          ? 'Personal Assistant to the District Collector, Erode District.'
          : 'மாவட்ட ஆட்சித்தலைவர் அவர்களின் உத்தரவுப்படி, ஈரோடு மாவட்டம்.';
      }

      // Expand numbered items into separate paragraphs for clean spacing and no page-break gaps
      const expandedBodyParas = [];
      for (const para of cleanBodyParas) {
        const lines = para.split('\n').map(l => l.trim()).filter(Boolean);
        let currentGroup = [];
        for (const line of lines) {
          const isNumbered = /^\d+[\.\)]\s*/.test(line) || /^[•\-\*]\s*/.test(line);
          if (isNumbered && currentGroup.length > 0) {
            expandedBodyParas.push(currentGroup.join('\n'));
            currentGroup = [line];
          } else {
            currentGroup.push(line);
          }
        }
        if (currentGroup.length > 0) {
          expandedBodyParas.push(currentGroup.join('\n'));
        }
      }

      if (result.template_type === 'meeting_minutes') {
        const headerBlock = isEnglishDoc ? `
          <div style="text-align: center; font-weight: bold; font-size: 12pt; color: #000000; line-height: 1.45; margin-bottom: 12px;">
            PROCEEDINGS OF THE DISTRICT COLLECTOR & DISTRICT MAGISTRATE, ERODE<br/>
            MINUTES OF REVIEW MEETING: ${result.subject.toUpperCase()}<br/>
            <span style="font-size: 11pt;">PRESENT: THIRU S. KANDASAMY, I.A.S., DISTRICT COLLECTOR</span>
          </div>
        ` : `
          <div style="text-align: center; font-weight: bold; font-size: 12pt; color: #000000; line-height: 1.45; margin-bottom: 12px;">
            ஈரோடு மாவட்ட ஆட்சித்தலைவர் அவர்கள் தலைமையில் ${result.date_display} அன்று<br/>
            நடைபெற்ற ${result.subject} கூட்ட நடவடிக்கைகள்<br/>
            <span style="font-size: 11pt;">முன்னிலை: திரு.ச.கந்தசாமி, இ.ஆ.ப.,</span>
          </div>
        `;

        const subHeaderBlock = isEnglishDoc ? `
          <div style="margin-bottom: 14px; font-size: 10.5pt; color: #000000; line-height: 1.6;">
            <div><strong>Roc. No:</strong> ${result.ref_number}/2026 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <strong>Dated:</strong> ${result.date_display}</div>
            <div style="margin-top: 6px;"><strong>Sub:</strong> ${result.subject} – Minutes of Review Meeting – Approval and Orders – Issued.</div>
            <div style="color: #222; margin-top: 4px;">Ref: G.O. Ms. No. 78, Agriculture & Farmers Welfare Department, dated 17.02.2016.</div>
            <div style="text-align: center; font-weight: bold; letter-spacing: 2px; margin-top: 6px;">&lt;&gt;&lt;&gt;&lt;&gt;</div>
          </div>
        ` : `
          <div style="margin-bottom: 14px; font-size: 10.5pt; color: #000000; line-height: 1.6;">
            <div><strong>எண்:</strong> வே/${result.ref_number}/2026 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <strong>நாள்:</strong> ${result.date_display}</div>
            <div style="margin-top: 6px;"><strong>பொருள்:</strong> ${result.subject} – கூட்ட நடவடிக்கைகள் – ஒப்புதல் அளித்தல் – தொடர்பாக.</div>
            <div style="color: #222; margin-top: 4px;">பார்வை: அரசாணை எண்: 78 வேளாண்மை (வே.உ.6) துறை, நாள்: 17.02.2016.</div>
            <div style="text-align: center; font-weight: bold; letter-spacing: 2px; margin-top: 6px;">&lt;&gt;&lt;&gt;&lt;&gt;</div>
          </div>
        `;

        container.innerHTML = `
          <div style="page-break-inside: avoid; break-inside: avoid;">
            ${headerBlock}
            <div style="border-top: 1.5px solid #000000; border-bottom: 1.5px solid #000000; padding: 6px 0; margin-bottom: 14px;">
              ${subHeaderBlock}
            </div>
          </div>

          <div style="color: #000000; font-size: 10.5pt; line-height: 1.75;">
            ${expandedBodyParas.map(p => {
              const isNumbered = /^\d+[\.\)]/.test(p.trim());
              return `
                <div style="margin-bottom: ${isNumbered ? '8px' : '12px'}; text-align: justify; color: #000000;">
                  ${p.replace(/\n/g, '<br/>')}
                </div>
              `;
            }).join('')}
          </div>

          <div style="page-break-inside: avoid; break-inside: avoid; margin-top: 25px;">
            <div style="display: flex; justify-content: flex-end; text-align: right; font-weight: bold; font-size: 10.5pt; color: #000000; margin-bottom: 15px;">
              <div>
                ${isEnglishDoc ? 'Sd/- S. Kandasamy<br/>District Collector,<br/>Erode District.' : 'ஓம்/-ச.கந்தசாமி<br/>மாவட்ட ஆட்சித்தலைவர்,<br/>ஈரோடு.'}
              </div>
            </div>
            <div style="text-align: center; font-size: 10pt; color: #333333; line-height: 1.5;">
              <div>${isEnglishDoc ? '/ By Order /' : '/உத்தரவுப்படி/'}</div>
              <div style="margin-top: 10px; font-weight: bold;">
                ${isEnglishDoc ? 'Personal Assistant to District Collector, District Collectorate, Erode.' : 'நேர்முக உதவியாளர், மாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.'}
              </div>
            </div>
          </div>
        `;
      } else {
        container.innerHTML = `
          <div style="page-break-inside: avoid; break-inside: avoid;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: bold; font-size: 11pt; color: #000000; margin-bottom: 18px;">
              <span>${refPrefixLabel}</span>
              <span>${isEnglishDoc ? `DATE: ${result.date_display}` : `நாள் - ${result.date_display}`}</span>
            </div>

            <div style="text-align: center; margin-bottom: 20px;">
              <div style="font-weight: bold; font-size: 12.5pt; color: #000000; line-height: 1.5;">
                ${headerTitle}
              </div>
              <div style="font-weight: bold; color: #000000; letter-spacing: 2px; margin-top: 6px;">----</div>
            </div>
          </div>

          <div style="color: #000000; font-size: 11pt; line-height: 1.75;">
            ${expandedBodyParas.map(p => {
              const isNumbered = /^\d+[\.\)]/.test(p.trim());
              return `
                <div style="margin-bottom: ${isNumbered ? '8px' : '12px'}; text-align: justify; color: #000000; font-size: 11pt; line-height: 1.75;">
                  ${p.replace(/\n/g, '<br/>')}
                </div>
              `;
            }).join('')}
          </div>

          <div style="page-break-inside: avoid; break-inside: avoid; margin-top: 25px; border-top: 1.5px solid #000000; padding-top: 10px;">
            <div style="font-weight: bold; font-size: 10.5pt; color: #000000;">
              ${footerLabel}
            </div>
          </div>
        `;
      }

      const opt = {
        margin: [12, 12, 12, 12],
        filename: filename,
        image: { type: 'jpeg', quality: 1.0 },
        html2canvas: { scale: 2.5, useCORS: true, letterRendering: true, backgroundColor: '#ffffff' },
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
    navigator.clipboard.writeText(result.generated_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleReset() {
    setResult(null);
    setError(null);
    setSubject('');
    setDetails('');
    setIsFormOpen(true);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Stamp size={20} style={{ color: 'var(--color-tn-accent)' }} />
        <span className="tamil-text" style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--color-text-primary)' }}>
          அதிகாரப்பூர்வ உள்ளடக்க ஜெனரேட்டர்
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8 }}>
        {TEMPLATES.map((tmpl) => {
          const Icon = tmpl.icon;
          const isActive = selectedTemplate === tmpl.id;
          return (
            <button
              key={tmpl.id}
              onClick={() => {
                setSelectedTemplate(tmpl.id);
                setResult(null);
                setError(null);
                setIsFormOpen(true);
              }}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4,
                padding: '10px 12px', borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                border: isActive ? `2px solid ${tmpl.color}` : '1px solid var(--color-surface-border)',
                background: isActive ? `${tmpl.color}15` : 'var(--color-surface-card)',
                boxShadow: isActive ? `0 0 12px ${tmpl.color}25` : 'none',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <Icon size={18} style={{ color: tmpl.color }} />
                {isActive && <ChevronRight size={14} style={{ color: tmpl.color }} />}
              </div>
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--color-text-primary)' }} className="tamil-text">
                {tmpl.titleTa}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                {tmpl.titleEn}
              </div>
            </button>
          );
        })}
      </div>

      <div ref={formRef} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
              {activeTmpl.titleTa} ({activeTmpl.titleEn}) — உள்ளீடுகள்
            </span>
            {result && (
              <span style={{
                padding: '2px 8px', borderRadius: 12, fontSize: '0.68rem', fontWeight: 600,
                background: 'rgba(59,130,246,0.12)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.25)',
              }}>
                {isFormOpen ? 'Click to minimize' : 'Click to view inputs'}
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
                  width: '100%', padding: '10px 12px', borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)', color: 'var(--color-text-primary)',
                  fontSize: '0.92rem', resize: 'vertical',
                }}
              />
            </div>

            <div>
              <label className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 600, display: 'block', marginBottom: 4, color: 'var(--color-text-primary)' }}>
                கூடுதல் விவரங்கள் & குறிப்புகள் (Detailed Notes / Key Points)
              </label>
              <textarea
                rows={3}
                placeholder={activeTmpl.detailPlaceholder}
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                className="tamil-text"
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 8,
                  border: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-input)', color: 'var(--color-text-primary)',
                  fontSize: '0.9rem', resize: 'vertical',
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
                color: '#fff', fontWeight: 700, fontSize: '1rem', cursor: 'pointer',
              }}
            >
              {loading ? <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> உருவாக்குகிறது...</> : 'ஆவணம் உருவாக்கு'}
            </button>
          </form>
        )}
      </div>

      {result && (
        <div ref={resultRef} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {/* Copy */}
              <button onClick={handleCopy} style={btnStyle()} title="Copy text to clipboard">
                {copied ? <><CheckCheck size={13} /> Copied!</> : <><Copy size={13} /> Copy</>}
              </button>

              {/* PDF */}
              <button
                onClick={handleExportPdf}
                disabled={exportingPdf}
                style={btnStyle()}
                title="Download as PDF file (.pdf)"
              >
                {exportingPdf ? (
                  <><RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> Exporting...</>
                ) : (
                  <><Download size={13} /> PDF</>
                )}
              </button>

              {/* DOCX */}
              <button
                onClick={handleExport}
                disabled={exporting}
                style={btnStyle(activeTmpl.color, true)}
                title="Download as Microsoft Word document (.docx)"
              >
                {exporting ? (
                  <><RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> Exporting...</>
                ) : (
                  <><Download size={13} /> DOCX</>
                )}
              </button>

              {/* New document */}
              <button onClick={handleReset} style={btnStyle()} title="Start a fresh new document">
                <Plus size={13} /> New Document
              </button>
            </div>
          </div>

          {/* Generated text preview */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{
              padding: '10px 16px', borderBottom: '1px solid var(--color-surface-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'var(--color-surface-hover)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileText size={14} style={{ color: 'var(--color-text-secondary)' }} />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                  Document Preview
                </span>
              </div>
            </div>

            <pre className="tamil-text" style={{
              padding: '16px 20px', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              fontFamily: "'Nirmala UI', 'Noto Sans Tamil', monospace",
              fontSize: '1rem', lineHeight: 1.8,
              color: 'var(--color-text-primary)',
              maxHeight: 480, overflowY: 'auto',
            }}>
              {result.generated_text}
            </pre>
          </div>
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
