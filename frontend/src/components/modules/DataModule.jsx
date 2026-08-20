import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import {
  fetchDatasets,
  fetchDatasetSchema,
  uploadDataset,
  queryDataset,
  detectOutliers,
  createCustomChart,
  deleteDatasetApi,
} from '../../lib/api';
import ConfidenceBadge from '../shared/ConfidenceBadge';
import {
  BarChart3,
  Upload,
  Search,
  Database,
  Table,
  Sparkles,
  AlertTriangle,
  Code2,
  FileSpreadsheet,
  RefreshCw,
  Trash2,
  ChevronRight,
  TrendingUp,
  Download,
  Eye,
  CheckCircle2,
} from 'lucide-react';

const SUGGESTED_QUESTIONS = {
  budget: [
    "வட்ட வாரியாக பட்ஜெட் ஒதுக்கீடு மற்றும் செலவு விபரம்",
    "சத்தியமங்கலம் மற்றும் ஈரோடு வட்டங்களின் நிதி பயன்பாட்டை ஒப்பிடு",
    "அதிக பட்ஜெட் ஒதுக்கீடு பெற்ற முதல் 5 வட்டங்கள்",
    "மொத்த மாவட்ட பட்ஜெட் மற்றும் சராசரி செலவு சுருக்கம்",
  ],
  patta: [
    "வட்ட வாரியாக நிலுவை பட்டா மாறுதல் வழக்குகள்",
    "ஈரோடு மற்றும் பவானி வட்டங்களில் தீர்க்கப்பட்ட வழக்குகளை ஒப்பிடு",
    "அதிக நிலுவை வழக்குகள் உள்ள முதல் 3 வட்டங்கள்",
    "மாவட்டத்தில் தீர்க்கப்பட்ட மொத்த மனுக்கள் எத்தனை?",
  ],
  pension: [
    "வட்ட வாரியாக முதியோர் மற்றும் விதவை உதவித்தொகை பயனாளிகள்",
    "மாதாந்திர பட்டுவாடா தொகை வட்ட வாரியாக ஒப்பீடு",
    "அதிக பயனாளிகள் உள்ள முதல் 5 வட்டங்கள்",
  ],
  default: [
    "வட்ட வாரியான புள்ளிவிவரங்கள் சுருக்கம்",
    "அதிகபட்ச மற்றும் குறைந்தபட்ச மதிப்புகளை ஒப்பிடு",
    "மாவட்ட சராசரி மற்றும் மொத்த விபரங்கள்",
  ]
};

export default function DataModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();

  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [datasetSchema, setDatasetSchema] = useState(null);
  const [activeTab, setActiveTab] = useState('query'); // 'query' | 'schema' | 'outliers' | 'custom_chart'

  // Query state
  const [question, setQuestion] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [showCodeAudit, setShowCodeAudit] = useState(false);

  // Outlier state
  const [selectedOutlierCol, setSelectedOutlierCol] = useState('');
  const [outlierResults, setOutlierResults] = useState(null);
  const [outlierLoading, setOutlierLoading] = useState(false);

  // Custom Chart Builder state (100% Dynamic for ANY Dataset)
  const [customChartType, setCustomChartType] = useState('bar');
  const [customXCol, setCustomXCol] = useState('');
  const [customYCol, setCustomYCol] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customChartResult, setCustomChartResult] = useState(null);
  const [customChartLoading, setCustomChartLoading] = useState(false);

  // Upload & UI states
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load all available datasets on mount
  useEffect(() => {
    loadDatasetsList();
  }, []);

  const loadDatasetsList = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDatasets();
      const list = res.datasets || [];
      setDatasets(list);
      if (list.length > 0 && !selectedDatasetId) {
        selectDataset(list[0].dataset_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectDataset = async (dsId) => {
    setSelectedDatasetId(dsId);
    setQueryResult(null);
    setOutlierResults(null);
    setCustomChartResult(null);
    try {
      const schemaData = await fetchDatasetSchema(dsId);
      setDatasetSchema(schemaData);
      // Pick defaults for outlier and custom chart builder
      const numCol = schemaData.columns?.find((c) => c.data_type_detected === 'number');
      const catCol = schemaData.columns?.find((c) => c.data_type_detected === 'text' || c.is_taluk_column);
      if (numCol) {
        setSelectedOutlierCol(numCol.column_name);
        setCustomYCol(numCol.column_name);
      }
      if (catCol) {
        setCustomXCol(catCol.column_name);
      }
      if (catCol && numCol) {
        setCustomTitle(`${catCol.column_name} வாரியான ${numCol.column_name}`);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGenerateCustomChart = async () => {
    if (!selectedDatasetId || !customXCol || !customYCol) return;
    setCustomChartLoading(true);
    setError(null);
    try {
      const res = await createCustomChart(
        selectedDatasetId,
        customChartType,
        customXCol,
        customYCol,
        customTitle || 'தனிப்பயன் வரைபடம்',
        officerId
      );
      setCustomChartResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setCustomChartLoading(false);
    }
  };


  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const newDs = await uploadDataset(file, officerId);
      await loadDatasetsList();
      if (newDs?.dataset_id) {
        selectDataset(newDs.dataset_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDataset = async (dsId, e) => {
    e.stopPropagation();
    if (!window.confirm("இந்த தரவுத்தொகுப்பை நீக்க விரும்புகிறீர்களா?")) return;
    try {
      await deleteDatasetApi(dsId, officerId);
      await loadDatasetsList();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleExecuteQuery = async (qText) => {
    const textToRun = qText || question;
    if (!textToRun.trim() || !selectedDatasetId) return;

    setQueryLoading(true);
    setError(null);
    try {
      const res = await queryDataset(selectedDatasetId, textToRun.trim(), officerId, 'both');
      setQueryResult(res);
      if (qText) setQuestion(qText);
    } catch (err) {
      setError(err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleRunOutliers = async () => {
    if (!selectedDatasetId || !selectedOutlierCol) return;
    setOutlierLoading(true);
    setError(null);
    try {
      const res = await detectOutliers(selectedDatasetId, selectedOutlierCol, 'iqr');
      setOutlierResults(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setOutlierLoading(false);
    }
  };

  // Dynamically generate intelligent suggested questions based on the actual columns of ANY uploaded dataset
  const getPromptSuggestions = () => {
    if (!datasetSchema || !datasetSchema.columns || datasetSchema.columns.length === 0) {
      return SUGGESTED_QUESTIONS.default;
    }

    const cols = datasetSchema.columns;
    const catCol = cols.find((c) => c.is_taluk_column || c.is_department_column || c.is_categorical || c.data_type_detected === 'text')?.column_name;
    const numCol = cols.find((c) => c.is_amount_column || c.data_type_detected === 'number')?.column_name;
    const secondNumCol = cols.filter((c) => c.data_type_detected === 'number')[1]?.column_name;

    const dynamicQuestions = [];

    if (catCol && numCol) {
      dynamicQuestions.push(`${catCol} வாரியாக ${numCol} விபரம்`);
      dynamicQuestions.push(`அதிக ${numCol} உள்ள முதல் 5 ${catCol}`);
    }

    if (catCol && numCol && secondNumCol) {
      dynamicQuestions.push(`${catCol} வாரியாக ${numCol} மற்றும் ${secondNumCol} ஒப்பீடு`);
    } else if (numCol) {
      dynamicQuestions.push(`மொத்த ${numCol} மற்றும் மாவட்ட சராசரி`);
    }

    if (catCol) {
      dynamicQuestions.push(`${catCol} வாரியான மொத்த புள்ளிவிவரங்கள் சுருக்கம்`);
    }

    if (dynamicQuestions.length >= 2) {
      return dynamicQuestions;
    }

    return SUGGESTED_QUESTIONS.default;
  };


  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="module-title tamil-text">{t('sidebar.data')}</h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
            மாவட்ட Excel / CSV தரவுகளை பகுப்பாய்வு செய்து தானியங்கி வரைபடங்கள், நுண்ணறிவுகள் மற்றும் முரண்பாடுகளை கண்டறியவும்
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={loadDatasetsList} disabled={loading} title="புதுப்பி">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => document.getElementById('data-module-upload').click()}
            disabled={uploading}
          >
            <Upload size={14} />
            <span className="tamil-text">{uploading ? 'பதிவேற்றுகிறது...' : 'புதிய கோப்பு பதிவேற்றம்'}</span>
          </button>
          <input
            id="data-module-upload"
            type="file"
            accept=".xlsx,.xls,.csv"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
        </div>
      </div>

      {error && (
        <div style={{ padding: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 8, fontSize: '0.85rem', display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Dataset Selection Pills */}
      <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4 }}>
        {datasets.map((ds) => {
          const isSelected = ds.dataset_id === selectedDatasetId;
          return (
            <div
              key={ds.dataset_id}
              onClick={() => selectDataset(ds.dataset_id)}
              className="card"
              style={{
                cursor: 'pointer',
                padding: '10px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                minWidth: 240,
                borderColor: isSelected ? 'var(--color-tn-accent)' : 'var(--color-surface-border)',
                background: isSelected ? 'rgba(200, 169, 81, 0.1)' : 'var(--color-surface-card)',
                boxShadow: isSelected ? '0 2px 8px rgba(200, 169, 81, 0.2)' : 'none',
              }}
            >
              <FileSpreadsheet size={20} style={{ color: isSelected ? 'var(--color-tn-accent)' : 'var(--color-text-muted)' }} />
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', color: 'var(--color-text-primary)' }}>
                  {ds.file_name}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', marginTop: 2 }}>
                  {ds.row_count} வரிசைகள் | {ds.column_count} நெடுவரிசைகள்
                </div>
              </div>
              <button
                onClick={(e) => handleDeleteDataset(ds.dataset_id, e)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', padding: 4 }}
                title="நீக்கு"
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Main Analysis Container */}
      {datasetSchema && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Sub Navigation Tabs */}
          <div className="tabs" style={{ marginBottom: 0 }}>
            <button
              className={`tab tamil-text ${activeTab === 'query' ? 'active' : ''}`}
              onClick={() => setActiveTab('query')}
            >
              <Search size={14} style={{ display: 'inline', marginRight: 6 }} />
              இயல்பான தமிழ் வினவல் (Natural Language Query)
            </button>
            <button
              className={`tab tamil-text ${activeTab === 'custom_chart' ? 'active' : ''}`}
              onClick={() => setActiveTab('custom_chart')}
            >
              <BarChart3 size={14} style={{ display: 'inline', marginRight: 6 }} />
              தனிப்பயன் வரைபடம் (Custom Chart Builder)
            </button>
            <button
              className={`tab tamil-text ${activeTab === 'schema' ? 'active' : ''}`}
              onClick={() => setActiveTab('schema')}
            >
              <Table size={14} style={{ display: 'inline', marginRight: 6 }} />
              நெடுவரிசை விவரம் (Schema & Profiling)
            </button>
            <button
              className={`tab tamil-text ${activeTab === 'outliers' ? 'active' : ''}`}
              onClick={() => setActiveTab('outliers')}
            >
              <TrendingUp size={14} style={{ display: 'inline', marginRight: 6 }} />
              விதிவிலக்கு & முரண்பாடுகள் (IQR Outlier Detection)
            </button>
          </div>


          {/* ─── TAB 1: Natural Language Query & Visual Analytics ─────────────── */}
          {activeTab === 'query' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Question Input Box */}
              <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleExecuteQuery();
                  }}
                  style={{ display: 'flex', gap: 10 }}
                >
                  <input
                    type="text"
                    placeholder="எ.கா: வட்ட வாரியாக பட்ஜெட் ஒதுக்கீடு மற்றும் செலவு விபரம்..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    className="tamil-text"
                    style={{
                      flex: 1,
                      padding: '12px 16px',
                      borderRadius: 8,
                      border: '1px solid var(--color-surface-border)',
                      background: 'var(--color-surface-input)',
                      color: 'var(--color-text-primary)',
                      fontSize: '0.95rem',
                      outline: 'none',
                    }}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!question.trim() || queryLoading}
                    style={{ padding: '12px 24px' }}
                  >
                    <Search size={16} />
                    <span className="tamil-text">{queryLoading ? 'பகுப்பாய்வு செய்கிறது...' : 'வினவு'}</span>
                  </button>
                </form>

                {/* Suggested Question Pills */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 600 }} className="tamil-text">
                    பரிந்துரைக்கப்பட்ட வினவல்கள்:
                  </span>
                  {getPromptSuggestions().map((sug, i) => (
                    <button
                      key={i}
                      className="btn btn-ghost btn-sm tamil-text"
                      onClick={() => handleExecuteQuery(sug)}
                      style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                    >
                      <Sparkles size={12} style={{ color: 'var(--color-tn-accent)' }} />
                      <span>{sug}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Query Results Presentation */}
              {queryResult && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {/* Summary & Execution Latency Banner */}
                  <div className="card" style={{ borderLeft: '4px solid var(--color-tn-primary)', padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontWeight: 600 }} className="tamil-text">
                        பகுப்பாய்வு சுருக்கம் (Executive Summary):
                      </div>
                      <div className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: 4 }}>
                        {queryResult.result_summary_tamil}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                        ⏱️ {queryResult.execution_time_ms} ms | {queryResult.row_count_returned} வரிசைகள்
                      </span>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setShowCodeAudit(!showCodeAudit)}
                        title="குறியீட்டை பார்"
                      >
                        <Code2 size={14} />
                        <span style={{ fontSize: '0.75rem' }}>SQL / Code</span>
                      </button>
                    </div>
                  </div>

                  {/* SQL / Pandas Code Audit Drawer */}
                  {showCodeAudit && (
                    <div className="card" style={{ background: 'var(--color-surface-hover)', padding: 14 }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                        தணிக்கை குறியீடு (Audit Trail & Code Provenance):
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-tn-primary-light)', fontFamily: 'monospace' }}>
                        <strong>Generated SQL:</strong> {queryResult.generated_sql}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontFamily: 'monospace', marginTop: 4 }}>
                        <strong>Pandas Code:</strong> {queryResult.generated_code}
                      </div>
                    </div>
                  )}

                  {/* Visual Analytics Row: Chart (Left) + Insights (Right) */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 1.3fr) minmax(280px, 1fr)', gap: 16 }}>
                    {/* Chart Container */}
                    <div className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--color-surface-card)' }}>
                      {queryResult.chart_url ? (
                        <div style={{ width: '100%', textAlign: 'center' }}>
                          <img
                            src={queryResult.chart_url}
                            alt="Data Visualization Chart"
                            onError={(e) => {
                              const src = e.target.src;
                              if (!e.target.dataset.triedFallback) {
                                e.target.dataset.triedFallback = '1';
                                const filename = queryResult.chart_url.split('/').pop();
                                e.target.src = `/api/outputs/charts/${filename}`;
                              }
                            }}
                            style={{
                              width: '100%',
                              maxHeight: '460px',
                              objectFit: 'contain',
                              borderRadius: 8,
                              background: '#ffffff',
                              padding: 8,
                              border: '1px solid var(--color-surface-border)',
                              boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                            }}
                          />
                          <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
                            <a
                              href={queryResult.chart_url}
                              download={`Erode_Chart_${queryResult.query_id || 'export'}.png`}
                              className="btn btn-ghost btn-sm"
                              style={{ gap: 6, fontSize: '0.8rem' }}
                            >
                              <Download size={14} />
                              <span className="tamil-text">உயர் தெளிவுத்திறன் வரைபடம் பதிவிறக்கு (PNG)</span>
                            </a>
                          </div>
                        </div>
                      ) : (
                        <div style={{ padding: 40, color: 'var(--color-text-muted)', textAlign: 'center' }}>
                          விளக்கப்படம் உருவாக்கப்படவில்லை (அட்டவணை வடிவம்)
                        </div>
                      )}
                    </div>


                    {/* Grounded Insights Card */}
                    <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--color-surface-border)', paddingBottom: 8 }}>
                        <Sparkles size={16} style={{ color: 'var(--color-tn-accent)' }} />
                        <h3 className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                          அரசு வழிகாட்டுதல் நுண்ணறிவுகள் (Grounded Insights)
                        </h3>
                      </div>

                      {queryResult.insights?.length === 0 ? (
                        <p className="tamil-text" style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>நுண்ணறிவுகள் ஏதுமில்லை.</p>
                      ) : (
                        queryResult.insights.map((ins, i) => (
                          <div
                            key={i}
                            style={{
                              padding: 12,
                              background: 'var(--color-surface-hover)',
                              borderRadius: 8,
                              borderLeft: '3px solid var(--color-tn-accent)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 6,
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                                {ins.insight_type}
                              </span>
                              <ConfidenceBadge score={ins.confidence_score || 0.95} />
                            </div>
                            <div className="tamil-text" style={{ fontSize: '0.85rem', lineHeight: 1.6, color: 'var(--color-text-primary)' }}>
                              {ins.insight_tamil}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Result Data Table */}
                  {queryResult.result_data?.length > 0 && (
                    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                      <div style={{ padding: '12px 16px', background: 'var(--color-surface-hover)', borderBottom: '1px solid var(--color-surface-border)', fontWeight: 700, fontSize: '0.85rem' }} className="tamil-text">
                        கணக்கிடப்பட்ட முடிவு அட்டவணை ({queryResult.result_data.length} வரிசைகள்):
                      </div>
                      <div style={{ overflowX: 'auto', maxHeight: 300 }}>
                        <table className="data-table">
                          <thead>
                            <tr>
                              {Object.keys(queryResult.result_data[0]).map((col) => (
                                <th key={col} className="tamil-text">{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {queryResult.result_data.map((row, rIdx) => (
                              <tr key={rIdx}>
                                {Object.values(row).map((val, cIdx) => (
                                  <td key={cIdx} className="tamil-text">
                                    {typeof val === 'number' ? val.toLocaleString('ta-IN') : String(val ?? '—')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ─── TAB 2: Schema & Profiler View ───────────────────────────────── */}
          {activeTab === 'schema' && (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>நெடுவரிசை (Column)</th>
                    <th>தமிழ் பெயர்</th>
                    <th>வகை (Type)</th>
                    <th>தனித்துவ எண்ணிக்கை</th>
                    <th>பூஜ்ஜியங்கள் (Nulls)</th>
                    <th>குறைந்தபட்சம் (Min)</th>
                    <th>அதிகபட்சம் (Max)</th>
                    <th>சராசரி (Mean)</th>
                    <th>சிறப்பு குறிச்சொல்</th>
                  </tr>
                </thead>
                <tbody>
                  {datasetSchema.columns?.map((col) => (
                    <tr key={col.column_id || col.column_name}>
                      <td style={{ fontWeight: 700 }}>{col.column_name}</td>
                      <td className="tamil-text">{col.column_name_tamil || '—'}</td>
                      <td>
                        <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', fontWeight: 600, background: 'var(--color-surface-hover)' }}>
                          {col.data_type_detected}
                        </span>
                      </td>
                      <td>{col.distinct_count}</td>
                      <td>{col.null_count}</td>
                      <td>{col.min_value ?? '—'}</td>
                      <td>{col.max_value ?? '—'}</td>
                      <td>{col.mean_value ? col.mean_value.toLocaleString('ta-IN') : '—'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {col.is_taluk_column && (
                            <span style={{ padding: '2px 6px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700 }}>வட்டம்</span>
                          )}
                          {col.is_department_column && (
                            <span style={{ padding: '2px 6px', background: '#fef3c7', color: '#92400e', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700 }}>துறை</span>
                          )}
                          {col.is_amount_column && (
                            <span style={{ padding: '2px 6px', background: '#d1fae5', color: '#065f46', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700 }}>தொகை ₹</span>
                          )}
                          {col.is_date_column && (
                            <span style={{ padding: '2px 6px', background: '#f3e8ff', color: '#6b21a8', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700 }}>தேதி</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ─── TAB 3: Outlier & Anomaly Inspector ───────────────────────────── */}
          {activeTab === 'outliers' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card" style={{ padding: 18, display: 'flex', gap: 12, alignItems: 'center' }}>
                <label className="tamil-text" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                  எண் நெடுவரிசையை தேர்ந்தெடுக்கவும்:
                </label>
                <select
                  value={selectedOutlierCol}
                  onChange={(e) => setSelectedOutlierCol(e.target.value)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-surface-border)',
                    background: 'var(--color-surface-input)',
                    color: 'var(--color-text-primary)',
                    fontWeight: 600,
                  }}
                >
                  {datasetSchema.columns
                    ?.filter((c) => c.data_type_detected === 'number')
                    .map((c) => (
                      <option key={c.column_name} value={c.column_name}>
                        {c.column_name}
                      </option>
                    ))}
                </select>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleRunOutliers}
                  disabled={outlierLoading || !selectedOutlierCol}
                >
                  <TrendingUp size={14} />
                  <span className="tamil-text">{outlierLoading ? 'கணக்கிடுகிறது...' : '1.5x IQR முரண்பாடுகளை கண்டறி'}</span>
                </button>
              </div>

              {outlierResults && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700 }} className="tamil-text">
                    கண்டறியப்பட்ட முரண்பாடுகள் ({outlierResults.total_outliers}):
                  </div>

                  {outlierResults.outliers.length === 0 ? (
                    <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--color-tn-success)' }}>
                      <CheckCircle2 size={32} style={{ margin: '0 auto 8px' }} />
                      <div className="tamil-text" style={{ fontWeight: 600 }}>புள்ளிவிவர முரண்பாடுகள் ஏதுமில்லை (அனைத்து மதிப்புகளும் இயல்பான வரம்பில் உள்ளன).</div>
                    </div>
                  ) : (
                    outlierResults.outliers.map((outlier, i) => (
                      <div
                        key={i}
                        className="card"
                        style={{
                          borderLeft: '4px solid var(--color-tn-danger)',
                          padding: 16,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 6,
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, color: 'var(--color-tn-danger)' }}>
                            ⚠️ விலகல் காரணி: {outlier.deviation_factor}x இயல்புக்கு மேல்
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                            எதிர்பார்க்கப்பட்ட வரம்பு: ₹{outlier.expected_range[0]?.toLocaleString('ta-IN')} - ₹{outlier.expected_range[1]?.toLocaleString('ta-IN')}
                          </span>
                        </div>
                        <div className="tamil-text" style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {outlier.reason_tamil}
                        </div>
                        {outlier.row_context && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: 4 }}>
                            சூழல்: {Object.entries(outlier.row_context).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* ─── TAB 4: Dynamic Custom Chart Builder ───────────────────────── */}
          {activeTab === 'custom_chart' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }} className="tamil-text">
                  <BarChart3 size={18} style={{ color: 'var(--color-tn-accent)' }} />
                  <span>எந்தவொரு புதிய தரவுத்தொகுப்பிற்கும் தனிப்பயன் வரைபடத்தை உருவாக்கவும்:</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                  {/* Chart Type Selector */}
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                      வரைபட வகை (Chart Type)
                    </label>
                    <select
                      value={customChartType}
                      onChange={(e) => setCustomChartType(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontWeight: 600,
                      }}
                    >
                      <option value="bar">📊 செங்குத்து பட்டை (Bar Chart)</option>
                      <option value="horizontal_bar">📊 கிடைமட்ட பட்டை (Horizontal Bar)</option>
                      <option value="line">📈 கோட்டு வரைபடம் (Line Chart)</option>
                      <option value="pie">🥧 வட்ட விளக்கப்படம் (Pie Chart)</option>
                    </select>
                  </div>

                  {/* X Axis Dimension */}
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                      பிரிவு / பரிமாணம் (X-Axis Category)
                    </label>
                    <select
                      value={customXCol}
                      onChange={(e) => setCustomXCol(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontWeight: 600,
                      }}
                    >
                      {datasetSchema.columns?.map((c) => (
                        <option key={c.column_name} value={c.column_name}>
                          {c.column_name} ({c.data_type_detected})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Y Axis Metric */}
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                      எண் / அளவு (Y-Axis Metric)
                    </label>
                    <select
                      value={customYCol}
                      onChange={(e) => setCustomYCol(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontWeight: 600,
                      }}
                    >
                      {datasetSchema.columns
                        ?.filter((c) => c.data_type_detected === 'number')
                        .map((c) => (
                          <option key={c.column_name} value={c.column_name}>
                            {c.column_name}
                          </option>
                        ))}
                    </select>
                  </div>

                  {/* Title */}
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>
                      வரைபட தலைப்பு (Tamil Title)
                    </label>
                    <input
                      type="text"
                      value={customTitle}
                      onChange={(e) => setCustomTitle(e.target.value)}
                      placeholder="எ.கா: வட்ட வாரியான ஒப்பீடு"
                      className="tamil-text"
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleGenerateCustomChart}
                    disabled={customChartLoading || !customXCol || !customYCol}
                  >
                    <Sparkles size={16} />
                    <span className="tamil-text">{customChartLoading ? 'உருவாக்குகிறது...' : 'வரைபடத்தை உருவாக்கு (Generate Chart)'}</span>
                  </button>
                </div>
              </div>

              {/* Rendered Custom Chart Display */}
              {customChartResult && (
                <div className="card animate-fade-in" style={{ padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <img
                    src={customChartResult.chart_url}
                    alt="Custom Chart"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '520px',
                      objectFit: 'contain',
                      borderRadius: 8,
                      background: '#ffffff',
                      padding: 8,
                      border: '1px solid var(--color-surface-border)',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    }}
                  />
                  <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
                    <a
                      href={customChartResult.chart_url}
                      download={`Custom_Chart_${customChartResult.chart_id}.png`}
                      className="btn btn-ghost btn-sm"
                      style={{ gap: 6 }}
                    >
                      <Download size={14} />
                      <span className="tamil-text">உயர் தெளிவுத்திறன் வரைபடம் பதிவிறக்கு (PNG)</span>
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

