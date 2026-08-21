import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import {
  fetchDatasets,
  fetchDatasetSchema,
  fetchDatasetData,
  uploadDataset,
  queryDataset,
  deleteDatasetApi,
  fetchDynamicSuggestions,
  trackSuggestionClick,
} from '../../lib/api';
import ConfidenceBadge from '../shared/ConfidenceBadge';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Label,
} from 'recharts';
import {
  BarChart3,
  LineChart as LineIcon,
  PieChart as PieIcon,
  Activity,
  ScatterChart as ScatterIcon,
  Upload,
  Send,
  Mic,
  MicOff,
  Sparkles,
  RefreshCw,
  Trash2,
  FileSpreadsheet,
  Download,
  AlertTriangle,
  Table as TableIcon,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
  Layers,
  FileDown,
} from 'lucide-react';

const CHART_COLORS = [
  '#059669', // Emerald
  '#2563eb', // Blue
  '#d97706', // Amber
  '#7c3aed', // Purple
  '#db2777', // Pink
  '#0891b2', // Cyan
  '#ea580c', // Orange
  '#4f46e5', // Indigo
  '#16a34a', // Green
  '#dc2626', // Red
];

// Helper to format raw database/column names cleanly for Tamil administrative display
const formatColumnLabel = (colName) => {
  if (!colName) return '';
  return String(colName).replace(/_/g, ' ');
};

export default function DataModule() {
  const { t } = useTranslation();
  const { officerId } = useAppStore();

  // Active dataset state (user-uploaded)
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [datasetSchema, setDatasetSchema] = useState(null);
  const [datasetRows, setDatasetRows] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Single Active Chart Configuration (Administrative: Category & Metric)
  const [activeChartType, setActiveChartType] = useState('bar'); // 'bar' | 'line' | 'pie' | 'area' | 'scatter'
  const [selectedCategoryCol, setSelectedCategoryCol] = useState(''); // Dimension (e.g. வட்டம், துறை)
  const [selectedMetricCol, setSelectedMetricCol] = useState('');     // Measure (e.g. பெறப்பட்ட மனுக்கள், ஒதுக்கீடு)
  const [chartTitle, setChartTitle] = useState('');

  // Table pagination & search
  const [tableSearch, setTableSearch] = useState('');
  const [tablePage, setTablePage] = useState(0);
  const rowsPerPage = 10;

  // Conversational AI State
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [dynamicSuggestions, setDynamicSuggestions] = useState([]);
  const [initialInsights, setInitialInsights] = useState(null);

  const chatEndRef = useRef(null);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatLoading]);

  const selectDataset = async (dsId) => {
    setSelectedDatasetId(dsId);
    setError(null);
    try {
      const [schemaData, dataRes] = await Promise.all([
        fetchDatasetSchema(dsId),
        fetchDatasetData(dsId, 200).catch(() => ({ rows: [] })),
      ]);

      setDatasetSchema(schemaData);
      const rows = dataRes.rows || [];
      setDatasetRows(rows);

      // Auto-configure optimal Category (Dimension) and Metric (Measure) directly from file data
      const cols = schemaData.columns || [];
      const catCol =
        cols.find((c) => c.is_taluk_column)?.column_name ||
        cols.find((c) => c.is_department_column)?.column_name ||
        cols.find((c) => c.is_categorical || c.data_type_detected === 'text')?.column_name ||
        cols[0]?.column_name || '';

      const numCol =
        cols.find((c) => c.is_amount_column)?.column_name ||
        cols.find((c) => c.data_type_detected === 'number' && c.column_name !== catCol)?.column_name ||
        cols.find((c) => c.data_type_detected === 'number')?.column_name ||
        cols[1]?.column_name || '';

      setSelectedCategoryCol(catCol);
      setSelectedMetricCol(numCol);
      setChartTitle(`${formatColumnLabel(catCol)} வாரியான ${formatColumnLabel(numCol)} பகுப்பாய்வு`);

      // Generate structured Initial Insights from RAG & File Knowledge
      generateInitialConversation(schemaData, rows, catCol, numCol);

      // Fetch dynamic grounded suggestions from RAG pipeline
      loadDynamicSuggestions(schemaData);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadDynamicSuggestions = async (schema) => {
    try {
      const sugRes = await fetchDynamicSuggestions(
        schema.source_id || schema.dataset_id,
        'data_viz',
        officerId
      );
      if (sugRes?.suggestions?.length > 0) {
        setDynamicSuggestions(sugRes.suggestions);
        return;
      }
    } catch {
      // Dynamic fallback synthesized from actual columns
    }

    const cols = schema.columns || [];
    const cat = cols.find((c) => c.is_taluk_column || c.is_department_column || c.data_type_detected === 'text')?.column_name;
    const num = cols.find((c) => c.is_amount_column || c.data_type_detected === 'number')?.column_name;
    const num2 = cols.filter((c) => c.data_type_detected === 'number' && c.column_name !== num)[0]?.column_name;

    const fallbacks = [];
    if (cat && num) {
      fallbacks.push({
        suggestion_id: 'sug_1',
        text_tamil: `${formatColumnLabel(cat)} வாரியாக ${formatColumnLabel(num)} ஒப்பீடு`,
        text_english: `Compare ${num} by ${cat}`,
      });
      fallbacks.push({
        suggestion_id: 'sug_2',
        text_tamil: `அதிக ${formatColumnLabel(num)} உள்ள முதல் 3 ${formatColumnLabel(cat)}`,
        text_english: `Top 3 ${cat} with highest ${num}`,
      });
    }
    if (cat && num && num2) {
      fallbacks.push({
        suggestion_id: 'sug_3',
        text_tamil: `${formatColumnLabel(cat)} வாரியாக ${formatColumnLabel(num)} மற்றும் ${formatColumnLabel(num2)} விகிதம்`,
        text_english: `Ratio of ${num} and ${num2} across ${cat}`,
      });
    } else if (num) {
      fallbacks.push({
        suggestion_id: 'sug_4',
        text_tamil: `மொத்த ${formatColumnLabel(num)} மற்றும் மாவட்ட சராசரி புள்ளிவிவரம்`,
        text_english: `Total and average ${num}`,
      });
    }
    setDynamicSuggestions(fallbacks);
  };

  const generateInitialConversation = (schema, rows, catCol, numCol) => {
    const fileName = schema.file_name || 'dataset';
    const rowCount = schema.row_count || rows.length;
    const colCount = schema.columns?.length || 0;

    let highestEntity = '';
    let totalSum = 0;

    if (rows.length > 0 && catCol && numCol) {
      const sorted = [...rows].sort((a, b) => (Number(b[numCol]) || 0) - (Number(a[numCol]) || 0));
      if (sorted[0]) {
        highestEntity = `${sorted[0][catCol]} (${Number(sorted[0][numCol]).toLocaleString('ta-IN')})`;
      }
      totalSum = rows.reduce((acc, r) => acc + (Number(r[numCol]) || 0), 0);
    }

    const insights = {
      fileName,
      totalRows: rowCount,
      totalCols: colCount,
      primaryMetric: formatColumnLabel(numCol),
      categoryLabel: formatColumnLabel(catCol),
      highestEntity: highestEntity || 'ஈரோடு மாவட்டம்',
      totalSum: totalSum > 0 ? totalSum.toLocaleString('ta-IN') : null,
    };
    setInitialInsights(insights);

    // Initial greeting in chat stream
    setChatMessages([
      {
        id: 'msg_welcome',
        sender: 'ai',
        type: 'greeting',
        text: 'வணக்கம்! பதிவேற்றப்பட்ட கோப்பிலிருந்து தரவு நுண்ணறிவுகள் பெறப்பட்டுள்ளன. கேள்விகளைக் கேட்டு உடனடி பகுப்பாய்வு மற்றும் வரைபடங்களை உருவாக்கலாம்.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const newDs = await uploadDataset(file, officerId);
      if (newDs?.dataset_id) {
        selectDataset(newDs.dataset_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleClearDataset = async () => {
    if (!window.confirm('இந்த கோப்பை நீக்கிவிட்டு புதிய கோப்பை பதிவேற்ற விரும்புகிறீர்களா?')) return;
    if (selectedDatasetId) {
      try {
        await deleteDatasetApi(selectedDatasetId, officerId);
      } catch {
        // Continue clearing local state
      }
    }
    setSelectedDatasetId(null);
    setDatasetSchema(null);
    setDatasetRows([]);
    setChatMessages([]);
    setDynamicSuggestions([]);
    setInitialInsights(null);
  };

  const handleSendQuery = async (queryText) => {
    const textToSend = queryText || chatInput;
    if (!textToSend.trim() || !selectedDatasetId) return;

    const userMsgId = `user_${Date.now()}`;
    const newMessages = [
      ...chatMessages,
      {
        id: userMsgId,
        sender: 'user',
        text: textToSend.trim(),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];
    setChatMessages(newMessages);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await queryDataset(selectedDatasetId, textToSend.trim(), officerId, 'both');

      // Live sync: update active chart & table with calculated query results
      if (res.result_data?.length > 0) {
        setDatasetRows(res.result_data);
        const keys = Object.keys(res.result_data[0]);
        if (keys.length > 0) setSelectedCategoryCol(keys[0]);
        if (keys.length > 1) setSelectedMetricCol(keys[1]);
        setChartTitle(textToSend.trim());
      }

      setChatMessages((prev) => [
        ...prev,
        {
          id: `ai_${Date.now()}`,
          sender: 'ai',
          type: 'response',
          text: res.result_summary_tamil || 'பகுப்பாய்வு வெற்றிகரமாக முடிந்தது.',
          englishText: res.result_summary_english,
          insights: res.insights || [],
          rowCount: res.row_count_returned,
          latency: res.execution_time_ms,
          chartUrl: res.chart_url,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `ai_${Date.now()}`,
          sender: 'ai',
          type: 'error',
          text: `பகுப்பாய்வு பிழை: ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handlePromptChipClick = (suggestion) => {
    trackSuggestionClick(suggestion.suggestion_id).catch(() => {});
    handleSendQuery(suggestion.text_tamil);
  };

  const handleAskAboutChart = () => {
    const query = `${formatColumnLabel(selectedCategoryCol)} வாரியாக ${formatColumnLabel(selectedMetricCol)} வரைபடத்தின் முக்கிய அம்சங்கள் மற்றும் விளக்கம் தருக`;
    handleSendQuery(query);
  };

  // Download Generated Visual with Crisp White Background, Professional Header, and Clear Axis Labels
  const handleDownloadVisual = (format = 'png') => {
    const container = document.getElementById('erode-active-chart-svg');
    if (!container) return;
    const svgElem = container.querySelector('svg');
    if (!svgElem) return;

    // Clone SVG to ensure inline style purity for export
    const clonedSvg = svgElem.cloneNode(true);
    clonedSvg.setAttribute('style', 'background-color: #ffffff;');

    const svgData = new XMLSerializer().serializeToString(clonedSvg);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const DOMURL = window.URL || window.webkitURL || window;
    const svgUrl = DOMURL.createObjectURL(svgBlob);

    if (format === 'svg') {
      const link = document.createElement('a');
      link.href = svgUrl;
      link.download = `${(chartTitle || 'Erode_Visualization').replace(/\s+/g, '_')}.svg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      return;
    }

    // High-Resolution Canvas PNG Export with Crisp White Background & Title Header
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const bbox = svgElem.getBoundingClientRect();
      const chartWidth = bbox.width || 800;
      const chartHeight = bbox.height || 360;
      const headerHeight = 60;

      const totalWidth = chartWidth;
      const totalHeight = chartHeight + headerHeight;

      canvas.width = totalWidth * 2; // 2x DPI scale for ultra-crisp print quality
      canvas.height = totalHeight * 2;
      const ctx = canvas.getContext('2d');
      ctx.scale(2, 2);

      // 1. Pure Crisp White Background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, totalWidth, totalHeight);

      // 2. Draw Top Header Banner on Downloaded Image
      ctx.fillStyle = '#0f172a'; // Slate 900
      ctx.font = 'bold 16px Inter, Noto Sans Tamil, system-ui, sans-serif';
      ctx.fillText(chartTitle || 'தரவு பகுப்பாய்வு வரைபடம்', 24, 28);

      ctx.fillStyle = '#475569'; // Slate 600
      ctx.font = '12px Inter, Noto Sans Tamil, system-ui, sans-serif';
      ctx.fillText(`ஈரோடு மாவட்ட ஆட்சியரகம் | ${formatColumnLabel(selectedCategoryCol)} • ${formatColumnLabel(selectedMetricCol)}`, 24, 48);

      // Header Divider Line
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(24, 55);
      ctx.lineTo(totalWidth - 24, 55);
      ctx.stroke();

      // 3. Draw Chart SVG
      ctx.drawImage(img, 0, headerHeight);
      DOMURL.revokeObjectURL(svgUrl);

      // 4. Download Image
      const imgURI = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.href = imgURI;
      link.download = `${(chartTitle || 'Erode_Visualization').replace(/\s+/g, '_')}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };
    img.src = svgUrl;
  };

  // Export Graphics Data Table to CSV
  const handleExportTableCsv = () => {
    if (!datasetRows || datasetRows.length === 0) return;
    const headers = Object.keys(datasetRows[0]);
    const csvRows = [headers.join(',')];
    for (const row of datasetRows) {
      const values = headers.map((h) => {
        const val = row[h] ?? '';
        return `"${String(val).replace(/"/g, '""')}"`;
      });
      csvRows.push(values.join(','));
    }
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(datasetSchema?.file_name || 'dataset').replace(/\.[^/.]+$/, '')}_table_data.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Voice Input Speech-to-Text (Real-time Speed-to-Typing Streaming)
  const toggleVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('உங்கள் உலாவியில் குரல் உள்ளீடு வசதி இல்லை (Web Speech API is not supported). Chrome/Edge உலாவியைப் பயன்படுத்தவும்.');
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = 'ta-IN';
      recognition.continuous = false;
      recognition.interimResults = true; // Stream interim results in real-time

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          setChatInput(transcript);
        }
      };

      recognition.start();
    } catch (e) {
      console.error('Speech recognition error:', e);
      setIsListening(false);
    }
  };

  // Prepare chart data for Recharts directly from dataset rows
  const prepareChartData = () => {
    if (!datasetRows || datasetRows.length === 0 || !selectedCategoryCol) {
      return [];
    }

    return datasetRows.slice(0, 30).map((row) => {
      const catVal = String(row[selectedCategoryCol] ?? '—');
      const metricVal = Number(String(row[selectedMetricCol] ?? 0).replace(/,/g, '').replace(/₹/g, '')) || 0;
      return {
        name: catVal,
        value: metricVal,
        ...row,
      };
    });
  };

  const chartData = prepareChartData();

  // Filtered Table Rows
  const filteredRows = datasetRows.filter((row) => {
    if (!tableSearch.trim()) return true;
    const term = tableSearch.toLowerCase();
    return Object.values(row).some((v) => String(v).toLowerCase().includes(term));
  });

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage) || 1;
  const displayedRows = filteredRows.slice(tablePage * rowsPerPage, (tablePage + 1) * rowsPerPage);

  // Render Single Active Chart with Recharts (White Background, Black Marks, Explicit Axis Labels)
  const renderSingleChart = () => {
    if (!chartData || chartData.length === 0) {
      return (
        <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
          வரைபட தரவு கிடைக்கவில்லை (No chart data available)
        </div>
      );
    }

    const chartMargins = { top: 20, right: 30, left: 50, bottom: 85 };

    const formatYAxisTick = (val) => {
      if (typeof val !== 'number') return val;
      if (Math.abs(val) >= 10000000) return `${(val / 10000000).toFixed(1)}Cr`;
      if (Math.abs(val) >= 100000) return `${(val / 100000).toFixed(1)}L`;
      if (Math.abs(val) >= 1000) return `${(val / 1000).toFixed(0)}k`;
      return val;
    };

    switch (activeChartType) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={370}>
            <LineChart data={chartData} margin={chartMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                interval={0}
                angle={-40}
                textAnchor="end"
                height={75}
                dy={6}
                dx={-4}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                tickFormatter={formatYAxisTick}
              >
                <Label
                  value={formatColumnLabel(selectedMetricCol)}
                  angle={-90}
                  position="insideLeft"
                  offset={-15}
                  style={{ fill: '#475569', fontWeight: 700, fontSize: 11, textAnchor: 'middle' }}
                />
              </YAxis>
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(val) => [Number(val).toLocaleString('ta-IN'), formatColumnLabel(selectedMetricCol)]}
              />
              <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={3} dot={{ r: 5, fill: '#2563eb' }} activeDot={{ r: 7 }} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={370}>
            <PieChart>
              <Pie
                data={chartData.slice(0, 10)}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={115}
                paddingAngle={3}
                dataKey="value"
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={true}
                stroke="#ffffff"
                strokeWidth={2}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(val) => [Number(val).toLocaleString('ta-IN'), formatColumnLabel(selectedMetricCol)]}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={370}>
            <AreaChart data={chartData} margin={chartMargins}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#059669" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#059669" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                interval={0}
                angle={-40}
                textAnchor="end"
                height={75}
                dy={6}
                dx={-4}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                tickFormatter={formatYAxisTick}
              >
                <Label
                  value={formatColumnLabel(selectedMetricCol)}
                  angle={-90}
                  position="insideLeft"
                  offset={-15}
                  style={{ fill: '#475569', fontWeight: 700, fontSize: 11, textAnchor: 'middle' }}
                />
              </YAxis>
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(val) => [Number(val).toLocaleString('ta-IN'), formatColumnLabel(selectedMetricCol)]}
              />
              <Area type="monotone" dataKey="value" stroke="#059669" strokeWidth={2} fillOpacity={1} fill="url(#areaGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={370}>
            <ScatterChart margin={chartMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                type="category"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                angle={-40}
                textAnchor="end"
                height={75}
                dy={6}
                dx={-4}
              />
              <YAxis
                dataKey="value"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                tickFormatter={formatYAxisTick}
              >
                <Label
                  value={formatColumnLabel(selectedMetricCol)}
                  angle={-90}
                  position="insideLeft"
                  offset={-15}
                  style={{ fill: '#475569', fontWeight: 700, fontSize: 11, textAnchor: 'middle' }}
                />
              </YAxis>
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(val) => [Number(val).toLocaleString('ta-IN'), formatColumnLabel(selectedMetricCol)]}
              />
              <Scatter data={chartData} fill="#ea580c" />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'bar':
      default:
        return (
          <ResponsiveContainer width="100%" height={370}>
            <BarChart data={chartData} margin={chartMargins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                interval={0}
                angle={-40}
                textAnchor="end"
                height={75}
                dy={6}
                dx={-4}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#0f172a', fontWeight: 600 }}
                tickFormatter={formatYAxisTick}
              >
                <Label
                  value={formatColumnLabel(selectedMetricCol)}
                  angle={-90}
                  position="insideLeft"
                  offset={-15}
                  style={{ fill: '#475569', fontWeight: 700, fontSize: 11, textAnchor: 'middle' }}
                />
              </YAxis>
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(val) => [Number(val).toLocaleString('ta-IN'), formatColumnLabel(selectedMetricCol)]}
              />
              <Bar dataKey="value" fill="#059669" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="module-title tamil-text">{t('sidebar.data')}</h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }} className="tamil-text">
            ஈரோடு மாவட்ட ஆட்சியரகம் — ஆவணத் தரவு பகுப்பாய்வு மற்றும் காட்சிப்படுத்தல் பணிமனை
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => document.getElementById('data-upload-input').click()}
            disabled={uploading}
          >
            <Upload size={14} />
            <span className="tamil-text">{uploading ? 'பதிவேற்றுகிறது...' : 'புதிய கோப்பு பதிவேற்றம்'}</span>
          </button>
          <input
            id="data-upload-input"
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

      {/* If No Dataset Loaded — Prominent Upload Workspace */}
      {!datasetSchema ? (
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(5, 150, 105, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-tn-accent)' }}>
            <Upload size={32} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 6 }}>Upload Administrative Dataset</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
              Excel அல்லது CSV கோப்பைப் பதிவேற்றி உடனடி வரைபடங்கள், நுண்ணறிவுகள் மற்றும் RAG பரிந்துரைகளைப் பெறவும்
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => document.getElementById('data-upload-input').click()}
            style={{ padding: '10px 24px' }}
          >
            <Upload size={16} />
            <span>Browse Files</span>
          </button>
          <div style={{ display: 'flex', gap: 8, fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            <span style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--color-surface-hover)' }}>CSV</span>
            <span style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--color-surface-hover)' }}>XLS</span>
            <span style={{ padding: '2px 8px', borderRadius: 4, background: 'var(--color-surface-hover)' }}>XLSX</span>
          </div>
        </div>
      ) : (
        /* ─── TWO-SPLIT CONVERSATIONAL & VISUAL LAYOUT ─────────────────────── */
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1.35fr) minmax(320px, 1fr)', gap: 18, alignItems: 'start' }}>
          
          {/* ════ LEFT SPLIT: Visual Data Analytics & Single Chart ════════════ */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            
            {/* File Header Banner */}
            <div
              className="card"
              style={{
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderLeft: '4px solid var(--color-tn-accent)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden' }}>
                <FileSpreadsheet size={22} style={{ color: 'var(--color-tn-accent)', flexShrink: 0 }} />
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.88rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', color: 'var(--color-text-primary)' }}>
                    {datasetSchema.file_name}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', display: 'flex', gap: 8 }}>
                    <span>• {datasetSchema.row_count?.toLocaleString('ta-IN') || datasetRows.length} வரிசைகள்</span>
                    <span>• {datasetSchema.columns?.length || 0} தலைப்புகள்</span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '3px 10px',
                    borderRadius: 12,
                    background: 'rgba(5, 150, 105, 0.12)',
                    color: '#059669',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#059669', display: 'inline-block' }}></span>
                  ஆய்வு செய்யப்பட்டது (Analyzed)
                </span>
                <button
                  onClick={() => document.getElementById('data-upload-input').click()}
                  className="btn btn-ghost btn-sm"
                  style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                  title="Replace File"
                >
                  <Upload size={12} /> Replace
                </button>
                <button
                  onClick={handleClearDataset}
                  className="btn btn-ghost btn-sm"
                  style={{ color: 'var(--color-tn-danger)', padding: '4px 8px' }}
                  title="Clear File"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>

            {/* Controls Toolbar: Natural Administrative Labels (Category & Metric) + Chart Switcher */}
            <div className="card" style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                
                {/* Natural Administrative Column Selectors (No Math Terms) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
                    <Filter size={14} style={{ color: 'var(--color-tn-accent)' }} />
                    <span style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>பிரிவு (Category):</span>
                    <select
                      value={selectedCategoryCol}
                      onChange={(e) => {
                        setSelectedCategoryCol(e.target.value);
                        setChartTitle(`${formatColumnLabel(e.target.value)} வாரியான ${formatColumnLabel(selectedMetricCol)}`);
                      }}
                      style={{
                        padding: '5px 10px',
                        borderRadius: 6,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                      }}
                    >
                      {datasetSchema.columns?.map((c) => (
                        <option key={c.column_name} value={c.column_name}>
                          {formatColumnLabel(c.column_name)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
                    <Layers size={14} style={{ color: 'var(--color-tn-accent)' }} />
                    <span style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>அளவு (Metric):</span>
                    <select
                      value={selectedMetricCol}
                      onChange={(e) => {
                        setSelectedMetricCol(e.target.value);
                        setChartTitle(`${formatColumnLabel(selectedCategoryCol)} வாரியான ${formatColumnLabel(e.target.value)}`);
                      }}
                      style={{
                        padding: '5px 10px',
                        borderRadius: 6,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                      }}
                    >
                      {datasetSchema.columns
                        ?.filter((c) => c.data_type_detected === 'number' || c.is_amount_column)
                        .map((c) => (
                          <option key={c.column_name} value={c.column_name}>
                            {formatColumnLabel(c.column_name)}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                {/* Single Chart Type Switcher Pills */}
                <div style={{ display: 'flex', gap: 4, background: 'var(--color-surface-hover)', padding: 3, borderRadius: 8 }}>
                  <button
                    onClick={() => setActiveChartType('bar')}
                    className={`btn btn-sm ${activeChartType === 'bar' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', gap: 4, borderRadius: 6 }}
                    title="Bar Chart"
                  >
                    <BarChart3 size={13} />
                    <span>பட்டை (Bar)</span>
                  </button>
                  <button
                    onClick={() => setActiveChartType('line')}
                    className={`btn btn-sm ${activeChartType === 'line' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', gap: 4, borderRadius: 6 }}
                    title="Line Chart"
                  >
                    <LineIcon size={13} />
                    <span>கோடு (Line)</span>
                  </button>
                  <button
                    onClick={() => setActiveChartType('pie')}
                    className={`btn btn-sm ${activeChartType === 'pie' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', gap: 4, borderRadius: 6 }}
                    title="Donut / Pie Chart"
                  >
                    <PieIcon size={13} />
                    <span>வட்டம் (Pie)</span>
                  </button>
                  <button
                    onClick={() => setActiveChartType('area')}
                    className={`btn btn-sm ${activeChartType === 'area' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', gap: 4, borderRadius: 6 }}
                    title="Area Chart"
                  >
                    <Activity size={13} />
                    <span>பரப்பு (Area)</span>
                  </button>
                  <button
                    onClick={() => setActiveChartType('scatter')}
                    className={`btn btn-sm ${activeChartType === 'scatter' ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', gap: 4, borderRadius: 6 }}
                    title="Scatter Plot"
                  >
                    <ScatterIcon size={13} />
                    <span>புள்ளி (Scatter)</span>
                  </button>
                </div>
              </div>
            </div>

            {/* ─── ONLY ONE PROMINENT CHART DISPLAY (White Background, Black Labels, Explicit X & Y Labels) ─── */}
            <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 10, background: '#ffffff', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h3 className="tamil-text" style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                    {chartTitle || 'தரவு ஒப்பீட்டு வரைபடம்'}
                  </h3>
                  <span style={{ fontSize: '0.72rem', color: '#475569' }}>
                    {formatColumnLabel(selectedCategoryCol)} (பிரிவு) • {formatColumnLabel(selectedMetricCol)} (அளவு)
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {/* Download Visual Button (PNG) */}
                  <button
                    onClick={() => handleDownloadVisual('png')}
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: '0.75rem', gap: 5, color: '#0f172a', borderColor: '#cbd5e1' }}
                    title="Download Chart Image (PNG)"
                  >
                    <Download size={13} />
                    <span className="tamil-text">வரைபடம் பதிவிறக்கு (PNG)</span>
                  </button>

                  {/* Ask AI About Chart Button */}
                  <button
                    onClick={handleAskAboutChart}
                    className="btn btn-ghost btn-sm tamil-text"
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--color-tn-accent)',
                      borderColor: 'var(--color-tn-accent)',
                      borderWidth: '1px',
                      borderStyle: 'solid',
                      gap: 6,
                    }}
                  >
                    <Sparkles size={13} />
                    <span>Ask AI About This Chart</span>
                  </button>
                </div>
              </div>

              {/* Render Selected Chart (Wrapped with ID & White Canvas Export Container) */}
              <div
                id="erode-active-chart-svg"
                style={{
                  width: '100%',
                  marginTop: 8,
                  background: '#ffffff',
                  borderRadius: 8,
                  padding: '8px 4px',
                }}
              >
                {renderSingleChart()}
              </div>
            </div>

            {/* ─── GRAPHICS DATA TABLE (Directly Under Chart) ─────────────────── */}
            <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div
                style={{
                  padding: '12px 16px',
                  background: 'var(--color-surface-hover)',
                  borderBottom: '1px solid var(--color-surface-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <TableIcon size={16} style={{ color: 'var(--color-tn-accent)' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }} className="tamil-text">
                    வரைபட தரவு அட்டவணை (Graphics Data Table)
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    ({filteredRows.length} வரிசைகள்)
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ position: 'relative' }}>
                    <Search size={13} style={{ position: 'absolute', left: 8, top: 8, color: 'var(--color-text-muted)' }} />
                    <input
                      type="text"
                      placeholder="அட்டவணையில் தேடு..."
                      value={tableSearch}
                      onChange={(e) => {
                        setTableSearch(e.target.value);
                        setTablePage(0);
                      }}
                      className="tamil-text"
                      style={{
                        padding: '4px 8px 4px 26px',
                        borderRadius: 6,
                        border: '1px solid var(--color-surface-border)',
                        background: 'var(--color-surface-input)',
                        color: 'var(--color-text-primary)',
                        fontSize: '0.75rem',
                        width: 160,
                      }}
                    />
                  </div>

                  {/* Export CSV Button */}
                  <button
                    onClick={handleExportTableCsv}
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: '0.75rem', gap: 4 }}
                    title="Export Data as CSV"
                  >
                    <FileDown size={13} />
                    <span>CSV</span>
                  </button>
                </div>
              </div>

              {/* Table Data View with Clean Formatted Headers */}
              <div style={{ overflowX: 'auto', maxHeight: 320 }}>
                {displayedRows.length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                    பொருத்தமான தரவுகள் ஏதுமில்லை.
                  </div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        {Object.keys(displayedRows[0]).map((col) => (
                          <th key={col} className="tamil-text" style={{ fontSize: '0.75rem', padding: '8px 12px' }}>
                            {formatColumnLabel(col)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {displayedRows.map((row, rIdx) => (
                        <tr key={rIdx} style={{ background: rIdx % 2 === 1 ? 'rgba(255,255,255,0.015)' : 'transparent' }}>
                          {Object.values(row).map((val, cIdx) => (
                            <td key={cIdx} className="tamil-text" style={{ fontSize: '0.8rem', padding: '8px 12px' }}>
                              {typeof val === 'number' ? val.toLocaleString('ta-IN') : String(val ?? '—')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Table Pagination Controls */}
              {totalPages > 1 && (
                <div
                  style={{
                    padding: '8px 16px',
                    borderTop: '1px solid var(--color-surface-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  <span>பக்கம் {tablePage + 1} / {totalPages}</span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => setTablePage((p) => Math.max(0, p - 1))}
                      disabled={tablePage === 0}
                      style={{ padding: '3px 8px' }}
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => setTablePage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={tablePage >= totalPages - 1}
                      style={{ padding: '3px 8px' }}
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>

          {/* ════ RIGHT SPLIT: Conversational AI with File Knowledge ═════════ */}
          <div
            className="card"
            style={{
              padding: 0,
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(100vh - 170px)',
              minHeight: 620,
              maxHeight: 880,
              border: '1px solid var(--color-surface-border)',
              overflow: 'hidden',
            }}
          >
            {/* Conversational Header */}
            <div
              style={{
                padding: '14px 18px',
                borderBottom: '1px solid var(--color-surface-border)',
                background: 'var(--color-surface-hover)',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(5, 150, 105, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#059669' }}>
                <Sparkles size={18} />
              </div>
              <div>
                <h3 className="tamil-text" style={{ fontSize: '0.92rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                  தரவு AI-யிடம் கேட்கவும்
                </h3>
                <p style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', margin: 0 }}>
                  Ask questions & view automatic insights about your data
                </p>
              </div>
            </div>

            {/* Scrollable Conversation Stream */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
              }}
            >
              {/* Grounded Initial Data Insights Card */}
              {initialInsights && (
                <div
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    background: 'rgba(5, 150, 105, 0.06)',
                    border: '1px solid rgba(5, 150, 105, 0.2)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#059669', fontSize: '0.78rem', fontWeight: 700 }}>
                    <Sparkles size={14} />
                    <span>Initial Data Insights ({initialInsights.fileName})</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', lineHeight: 1.6, color: 'var(--color-text-primary)' }} className="tamil-text">
                    <p style={{ margin: '0 0 6px 0' }}>
                      பதிவேற்றப்பட்ட ஆவணத்தின் முதன்மை கண்டுபிடிப்புகள்:
                    </p>
                    <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <li>மொத்த பதிவுகள்: <strong>{initialInsights.totalRows.toLocaleString('ta-IN')}</strong> வரிசைகள் ({initialInsights.totalCols} தலைப்புகள்).</li>
                      <li>முதன்மை அளவீடு: <strong>'{initialInsights.primaryMetric}'</strong>.</li>
                      <li>அதிகபட்ச பதிவு உள்ள பகுதி: <strong>{initialInsights.highestEntity}</strong>.</li>
                      {initialInsights.totalSum && (
                        <li>மாவட்ட மொத்த அளவு: <strong>{initialInsights.totalSum}</strong>.</li>
                      )}
                      <li>பரிந்துரை: கீழே உள்ள RAG வினவல்களைப் பயன்படுத்தி ஒப்பீட்டு ஆய்வை மேற்கொள்ளலாம்.</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* Chat Message Stream */}
              {chatMessages.map((msg) => {
                const isAi = msg.sender === 'ai';
                return (
                  <div
                    key={msg.id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: isAi ? 'flex-start' : 'flex-end',
                      gap: 4,
                    }}
                  >
                    <div
                      style={{
                        maxWidth: '88%',
                        padding: '12px 16px',
                        borderRadius: isAi ? '12px 12px 12px 2px' : '12px 12px 2px 12px',
                        background: isAi ? 'var(--color-surface-hover)' : 'var(--color-tn-primary)',
                        color: isAi ? 'var(--color-text-primary)' : '#ffffff',
                        border: isAi ? '1px solid var(--color-surface-border)' : 'none',
                        fontSize: '0.84rem',
                        lineHeight: 1.6,
                        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                      }}
                    >
                      <div className="tamil-text">{msg.text}</div>
                      {msg.englishText && (
                        <div style={{ fontSize: '0.75rem', marginTop: 4, opacity: 0.85, fontStyle: 'italic' }}>
                          {msg.englishText}
                        </div>
                      )}

                      {/* Attached Grounded Insights in Response */}
                      {msg.insights?.length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {msg.insights.map((ins, i) => (
                            <div
                              key={i}
                              style={{
                                padding: '6px 10px',
                                background: 'rgba(0,0,0,0.15)',
                                borderRadius: 6,
                                fontSize: '0.75rem',
                                borderLeft: '2px solid var(--color-tn-accent)',
                              }}
                            >
                              <div className="tamil-text">{ins.insight_tamil}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', padding: '0 4px' }}>
                      {msg.timestamp}
                    </span>
                  </div>
                );
              })}

              {/* Thinking / Loading State */}
              {chatLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-muted)', fontSize: '0.8rem', padding: '6px 12px' }}>
                  <Sparkles size={14} className="animate-spin" style={{ color: 'var(--color-tn-accent)' }} />
                  <span className="tamil-text">தரவு AI பகுப்பாய்வு செய்கிறது...</span>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Dynamic RAG Prompt Suggestions Chips (Zero Hardcoding) */}
            {dynamicSuggestions.length > 0 && (
              <div
                style={{
                  padding: '10px 14px',
                  borderTop: '1px solid var(--color-surface-border)',
                  background: 'var(--color-surface-card)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                }}
              >
                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  RECOMMENDED PROMPTS
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', maxHeight: 80, overflowY: 'auto' }}>
                  {dynamicSuggestions.map((sug, i) => (
                    <button
                      key={sug.suggestion_id || i}
                      onClick={() => handlePromptChipClick(sug)}
                      disabled={chatLoading}
                      className="btn btn-ghost btn-sm tamil-text"
                      style={{
                        fontSize: '0.74rem',
                        padding: '4px 10px',
                        background: 'var(--color-surface-hover)',
                        borderRadius: 14,
                        gap: 6,
                        textAlign: 'left',
                      }}
                    >
                      <Sparkles size={11} style={{ color: 'var(--color-tn-accent)', flexShrink: 0 }} />
                      <span>{sug.text_tamil}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Bottom Conversational Input Box */}
            <div
              style={{
                padding: 12,
                borderTop: '1px solid var(--color-surface-border)',
                background: 'var(--color-surface-hover)',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendQuery();
                }}
                style={{ display: 'flex', gap: 8, alignItems: 'center' }}
              >
                <input
                  type="text"
                  placeholder="இந்த தரவுத்தொகுப்பு பற்றி AI-யிடம் கேட்கவும்..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="tamil-text"
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-surface-border)',
                    background: 'var(--color-surface-input)',
                    color: 'var(--color-text-primary)',
                    fontSize: '0.84rem',
                    outline: 'none',
                  }}
                />

                <button
                  type="button"
                  onClick={toggleVoiceInput}
                  className={`btn btn-sm ${isListening ? 'btn-danger' : 'btn-ghost'}`}
                  style={{ padding: '8px 10px', borderRadius: 8 }}
                  title={isListening ? 'Stop voice recording' : 'Voice input'}
                >
                  {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                </button>

                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={!chatInput.trim() || chatLoading}
                  style={{ padding: '8px 16px', borderRadius: 8, gap: 6 }}
                >
                  <span className="tamil-text">{chatLoading ? '...' : 'அனுப்பு'}</span>
                  <Send size={13} />
                </button>
              </form>
            </div>

          </div>

        </div>
      )}
    </div>
  );
}
