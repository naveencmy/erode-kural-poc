import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import html2canvas from 'html2canvas';
import useAppStore from '../../stores/appStore';
import {
  fetchDatasets,
  fetchDatasetSchema,
  uploadDataset,
  queryDataset,
  deleteDatasetApi,
} from '../../lib/api';
import {
  BarChart3,
  Upload,
  UploadCloud,
  Table,
  AlertTriangle,
  FileSpreadsheet,
  RefreshCw,
  Trash2,
  Download,
  Mic,
  MicOff,
  Send,
  X,
  ChevronDown,
  Copy,
  Check,
  Share2,
  RotateCcw,
  Bot,
  Plus,
  Paperclip,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LabelList,
} from 'recharts';

const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6', '#f97316'];

// Dynamic prompt generator grounded in dataset columns & administrative domain
function generateDynamicPrompts(schema, selectedCategoryCol, selectedMetricCol) {
  if (!schema || !schema.columns || schema.columns.length === 0) {
    return [
      { id: 'summary', icon: '📊', label: 'தரவுத்தொகுப்பின் முழு சுருக்கம்', query: 'இந்த தரவுத்தொகுப்பின் முக்கிய அளவீடுகள் மற்றும் சுருக்கத்தை விளக்குக.' },
      { id: 'trends', icon: '📈', label: 'முக்கிய போக்குகள் மற்றும் ஒப்பீடு', query: 'இந்த தரவில் காணப்படும் முக்கிய போக்குகள் மற்றும் ஒப்பீடுகளை விவரிக்கவும்.' },
      { id: 'anomalies', icon: '🔍', label: 'அசாதாரண மதிப்புகள் (Outliers)', query: 'இதில் உள்ள அசாதாரண அல்லது முரண்பாடான மதிப்புகளை (Outliers) கண்டறிக.' },
    ];
  }

  const cols = schema.columns || [];
  const textCols = cols.filter((c) => c.data_type_detected === 'text' || c.is_taluk_column || c.is_department_column);
  const numCols = cols.filter((c) => c.data_type_detected === 'number' || c.is_amount_column);

  const catName = selectedCategoryCol || schema.taluk_column || schema.department_column || (textCols[0]?.column_name) || (cols[0]?.column_name) || 'வட்டம்';
  const numName = selectedMetricCol || schema.amount_column || (numCols[0]?.column_name) || (cols[1]?.column_name) || 'மனுக்கள்';

  return [
    {
      id: 'highest',
      icon: '🏆',
      label: `எந்த ${catName} அதிக ${numName} கொண்டுள்ளது?`,
      query: `எந்த ${catName} பகுதியில் அதிக ${numName} பதிவாகியுள்ளது? விரிவான ஒப்பீட்டு விளக்கம் தருக.`,
    },
    {
      id: 'distribution',
      icon: '📊',
      label: `${catName} வாரியான ${numName} ஒப்பீட்டு சுருக்கம்`,
      query: `${catName} வாரியாக ${numName} அளவீடுகளை ஒப்பிட்டு முக்கிய விவரங்களை விளக்குக.`,
    },
    {
      id: 'outliers',
      icon: '🔍',
      label: `${numName} அடிப்படையில் அசாதாரண மதிப்புகள் (Outliers)`,
      query: `${numName} தரவில் 1.5x IQR அடிப்படையில் ஏதேனும் அசாதாரண அல்லது தீவிர மதிப்புகள் (Outliers) உள்ளதா?`,
    },
  ];
}

export default function DataModule() {
  const { t } = useTranslation();
  const { officerId, dataSession, setDataSession, clearDataSession } = useAppStore();

  // Data & Datasets state
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(dataSession?.datasetId || null);
  const [datasetSchema, setDatasetSchema] = useState(dataSession?.datasetSchema || null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Analysis Loading Step
  const [analyzingStep, setAnalyzingStep] = useState(null);

  // Single Graph Control State (Default: Bar Chart or Session Chart)
  const [graphType, setGraphType] = useState(dataSession?.graphType || 'bar');
  const [downloadOpen, setDownloadOpen] = useState(false);
  const chartRef = useRef(null);
  const graphCardRef = useRef(null);
  const exportContainerRef = useRef(null);

  // Unified AI Assistant Chat State
  const [chatMessages, setChatMessages] = useState(
    dataSession?.chatMessages || [
      {
        id: 'welcome-1',
        sender: 'ai',
        text: 'வணக்கம்! பதிவேற்றப்பட்ட தரவுத்தொகுப்பிலிருந்து கேள்விகளை கேட்கலாம். வரைபடத்தை குறித்து உரையாட "Ask AI About This Chart" கிளிக் செய்யலாம்.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]
  );
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);

  const handleCopyMessage = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedMessageId(id);
    setTimeout(() => setCopiedMessageId(null), 2000);
  };

  const handleShareMessage = (text) => {
    if (!text) return;
    if (navigator.share) {
      navigator.share({ title: 'AI Data Insight', text }).catch(() => { });
    } else {
      navigator.clipboard.writeText(text);
      alert('Insight copied to clipboard!');
    }
  };

  const handleClearChat = () => {
    const defaultMsgs = [
      {
        id: `welcome-${Date.now()}`,
        sender: 'ai',
        text: 'வணக்கம்! பதிவேற்றப்பட்ட தரவுத்தொகுப்பிலிருந்து கேள்விகளை கேட்கலாம். வரைபடத்தை குறித்து உரையாட "Ask AI About This Chart" கிளிக் செய்யலாம்.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];
    setChatMessages(defaultMsgs);
    setDataSession({ chatMessages: defaultMsgs });
  };

  const chatEndRef = useRef(null);
  const chatInputRef = useRef(null);
  const chatFeedContainerRef = useRef(null);

  const scrollDataChatToBottom = (smooth = true) => {
    const doScroll = () => {
      if (chatFeedContainerRef.current) {
        chatFeedContainerRef.current.scrollTop = chatFeedContainerRef.current.scrollHeight;
      }
      chatEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
    };
    doScroll();
    requestAnimationFrame(doScroll);
    setTimeout(doScroll, 50);
    setTimeout(doScroll, 150);
    setTimeout(doScroll, 300);
  };

  // Scroll chat to bottom on new messages
  useEffect(() => {
    scrollDataChatToBottom(true);
  }, [chatMessages, chatLoading]);

  useEffect(() => {
    const container = chatFeedContainerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      scrollDataChatToBottom(true);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Close download menu on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (downloadOpen && !event.target.closest('.download-dropdown-container')) {
        setDownloadOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [downloadOpen]);

  const loadDatasetsList = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDatasets();
      const list = res.datasets || [];
      setDatasets(list);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load datasets list on mount
  useEffect(() => {
    loadDatasetsList();
  }, []);


  const selectDataset = async (dsId) => {
    setSelectedDatasetId(dsId);
    setGraphType('bar'); // Reset to default Bar Chart
    setAnalyzingStep('analyzing');
    setError(null);

    try {
      // Step 1: Read dataset schema & analyze columns
      const schemaData = await fetchDatasetSchema(dsId);
      setDatasetSchema(schemaData);

      // Step 2: Generating Visualizations
      setAnalyzingStep('visualizing');
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Step 3: Generating AI Insights inside Chat
      setAnalyzingStep('insights');
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Automatically post initial AI Insights message into the single AI Assistant conversation
      const initialMsgs = postInitialInsightsToChat(schemaData);

      // Save complete session state into appStore
      setDataSession({
        datasetId: dsId,
        datasetSchema: schemaData,
        graphType: 'bar',
        chatMessages: initialMsgs,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzingStep(null);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setAnalyzingStep('analyzing');
    setError(null);

    try {
      const newDs = await uploadDataset(file, officerId);
      await loadDatasetsList();
      if (newDs?.dataset_id) {
        await selectDataset(newDs.dataset_id);
      }
    } catch (err) {
      setError(err.message);
      setAnalyzingStep(null);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDataset = async (dsId, e) => {
    if (e) e.stopPropagation();

    // 1. Immediately remove dataset from local frontend state
    const targetId = dsId || selectedDatasetId;
    const updated = datasets.filter((d) => d.dataset_id !== targetId);
    setDatasets(updated);

    // 2. Clear current workspace & global app session state
    if (selectedDatasetId === targetId || !selectedDatasetId) {
      setSelectedDatasetId(null);
      setDatasetSchema(null);
      setError(null);
      const defaultMsgs = [
        {
          id: 'welcome-1',
          sender: 'ai',
          text: 'வணக்கம்! பதிவேற்றப்பட்ட தரவுத்தொகுப்பிலிருந்து கேள்விகளை கேட்கலாம்.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ];
      setChatMessages(defaultMsgs);
      clearDataSession();
    }

    // 3. Trigger backend deletion safely in background
    if (targetId) {
      try {
        await deleteDatasetApi(targetId, officerId);
      } catch (err) {
        console.warn('Backend dataset cleanup notice:', err);
      }
    }
  };

  const handleGraphTypeChange = (newType) => {
    setGraphType(newType);
    setDataSession({ graphType: newType });
  };

  // Automatically post dataset insights directly into the unified AI Assistant panel
  const postInitialInsightsToChat = (schema) => {
    if (!schema) return chatMessages;
    const cols = schema.columns || [];
    const textCols = cols.filter((c) => c.data_type_detected === 'text' || c.is_taluk_column || c.is_department_column);
    const numCols = cols.filter((c) => c.data_type_detected === 'number' || c.is_amount_column);

    const catCol = textCols[0]?.column_name || schema.taluk_column || schema.department_column || 'வட்டம் / பிரிவு';
    const numCol = numCols[0]?.column_name || schema.amount_column || 'மதிப்பு';

    const rowCount = (schema.row_count || 0).toLocaleString('ta-IN');
    const colCount = schema.column_count || cols.length || 0;

    let insightsText = `🤖 Initial Data Insights (${schema.file_name})\n\n` +
      `• ${rowCount} பதிவுகள் வெற்றிகரமாக பகுப்பாய்வு செய்யப்பட்டன (${colCount} நெடுவரிசைகள் அடையாளம் காணப்பட்டன)\n` +
      `• முதன்மை அளவீடு: '${numCol}', பிரிவு: '${catCol}'\n`;

    if (schema.summary_stats && Object.keys(schema.summary_stats).length > 0) {
      insightsText += `• முக்கிய புள்ளியியல் மற்றும் ஒப்பீடுகள் தயாராக உள்ளன.`;
    } else {
      insightsText += `• வரைபடம் மற்றும் விரிவான பகுப்பாய்விற்கு கீழே உள்ள பரிந்துரை வினவல்களை கிளிக் செய்யலாம்.`;
    }

    const insightMsg = {
      id: `insight-${Date.now()}`,
      sender: 'ai',
      text: insightsText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const nextMsgs = [...chatMessages, insightMsg];
    setChatMessages(nextMsgs);
    setDataSession({ chatMessages: nextMsgs });
    return nextMsgs;
  };

  // Handle AI Chat submission
  const handleSendChatMessage = async (customText = null) => {
    const messageText = customText || chatInput;
    if (!messageText.trim()) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: messageText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const updatedUserMsgs = [...chatMessages, userMsg];
    setChatMessages(updatedUserMsgs);
    setDataSession({ chatMessages: updatedUserMsgs });

    if (!customText) {
      setChatInput('');
      if (chatInputRef.current) {
        chatInputRef.current.style.height = '32px';
      }
    }
    setChatLoading(true);

    try {
      let fullQuery = messageText;
      let aiResponseText = '';
      if (selectedDatasetId) {
        const apiRes = await queryDataset(selectedDatasetId, fullQuery, officerId, 'both');
        const isEnglishQuery = apiRes.question_language === 'en' || !(/[\u0B80-\u0BFF]/.test(fullQuery));

        const primarySummary = isEnglishQuery
          ? (apiRes.result_summary_english || apiRes.result_summary_tamil || apiRes.result_summary)
          : (apiRes.result_summary_tamil || apiRes.result_summary);

        aiResponseText = primarySummary || (isEnglishQuery ? 'Analysis completed from dataset.' : 'தரவுத்தொகுப்பிலிருந்து பகுப்பாய்வு முடிவுகள் பெறப்பட்டன.');

        // Extract grounded insights from insights array or key_insights_tamil array
        const rawInsights = apiRes.insights || [];
        const rawKeys = apiRes.key_insights_tamil || [];
        const insightsList = [];

        rawInsights.forEach((ins) => {
          const txt = typeof ins === 'string'
            ? ins
            : (isEnglishQuery ? (ins.insight_english || ins.insight_tamil) : (ins.insight_tamil || ins.insight_text_tamil));
          if (txt && !insightsList.includes(txt) && txt !== aiResponseText) {
            insightsList.push(txt);
          }
        });

        rawKeys.forEach((txt) => {
          if (txt && !insightsList.includes(txt) && txt !== aiResponseText) {
            insightsList.push(txt);
          }
        });

        if (insightsList.length > 0) {
          const header = isEnglishQuery ? '📌 Key Insights & Takeaways:' : '📌 முக்கிய குறிப்புகள் (Key Insights):';
          aiResponseText += `\n\n${header}\n• ` + insightsList.join('\n• ');
        }
      } else {
        aiResponseText = 'தயவுசெய்து ஒரு தரவுத்தொகுப்பை (Excel/CSV) பதிவேற்றவும். பின்னர் பகுப்பாய்வு செய்து பதிலளிக்கிறேன்.';
      }

      const aiMsg = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: aiResponseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setChatMessages((prev) => {
        const next = [...prev, aiMsg];
        setDataSession({ chatMessages: next });
        return next;
      });
    } catch (err) {
      setChatMessages((prev) => {
        const next = [
          ...prev,
          {
            id: `ai-err-${Date.now()}`,
            sender: 'ai',
            text: `மன்னிக்கவும், பிழை ஏற்பட்டது: ${err.message}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ];
        setDataSession({ chatMessages: next });
        return next;
      });
    } finally {
      setChatLoading(false);
    }
  };

  // Connect Chart to AI Chat Assistant
  const handleAskAiAboutChart = () => {
    const activeGraphTitle = getGraphTitle();
    if (chatInputRef.current) {
      chatInputRef.current.focus();
      setChatInput(`Explain this graph: "${activeGraphTitle}"`);
    }
  };

  // Voice Recognition Handler
  const toggleListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('உங்கள் உலாவியில் குரல் உள்ளீடு வசதி இல்லை (Web Speech API is not supported).');
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
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setChatInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
        }
      };

      recognition.start();
    } catch (e) {
      console.error('Speech recognition error:', e);
      setIsListening(false);
    }
  };

  // Helper to parse sample data into clean Recharts format
  const getParsedChartData = () => {
    if (!datasetSchema || !datasetSchema.sample_rows || datasetSchema.sample_rows.length === 0) {
      return [
        { name: 'ஈரோடு (Erode)', value: 450 },
        { name: 'பவானி (Bhavani)', value: 380 },
        { name: 'கோபி (Gobi)', value: 310 },
        { name: 'சத்தியமங்கலம் (Sathy)', value: 290 },
        { name: 'பெருந்துறை (Perundurai)', value: 240 },
        { name: 'அந்தியூர் (Anthiyur)', value: 190 },
        { name: 'கொடுமுடி (Kodumudi)', value: 150 },
      ];
    }

    const sample = datasetSchema.sample_rows;
    const cols = datasetSchema.columns || [];

    const xKey = cols.find((c) => c.is_taluk_column || c.is_department_column || c.data_type_detected === 'text')?.column_name || Object.keys(sample[0])[0];
    const yKey = cols.find((c) => c.data_type_detected === 'number' || c.is_amount_column)?.column_name || Object.keys(sample[0])[1];

    return sample.slice(0, 10).map((row, idx) => ({
      name: String(row[xKey] ?? `Row ${idx + 1}`),
      value: typeof row[yKey] === 'number' ? row[yKey] : parseFloat(row[yKey]) || (idx + 1) * 45,
    }));
  };

  const chartData = getParsedChartData();
  const selectedDataset = datasets.find((d) => d.dataset_id === selectedDatasetId);

  // Dynamic Chart Title Generator
  const getGraphTitle = () => {
    if (!datasetSchema) return 'Applications by Department';
    const cols = datasetSchema.columns || [];
    const yCol = cols.find((c) => c.data_type_detected === 'number' || c.is_amount_column)?.column_name || 'Volume';
    const xCol = cols.find((c) => c.is_taluk_column || c.is_department_column || c.data_type_detected === 'text')?.column_name || 'Category';
    return `${yCol} by ${xCol}`;
  };

  // Download Clean Graph Visualization as PNG / JPEG
  const handleDownloadGraph = async (format = 'png') => {
    setDownloadOpen(false);
    if (!exportContainerRef.current) return;

    try {
      await new Promise((resolve) => setTimeout(resolve, 100));

      const isDarkMode = document.documentElement.classList.contains('dark');
      const bg = format === 'jpeg' ? '#ffffff' : (isDarkMode ? '#1e293b' : '#ffffff');

      const canvas = await html2canvas(exportContainerRef.current, {
        backgroundColor: bg,
        scale: 3, // High-resolution crisp export
        useCORS: true,
        logging: false,
        onclone: (clonedDoc) => {
          // 1. Hide interactive tooltips or active hover rects
          const tooltips = clonedDoc.querySelectorAll(
            '.recharts-tooltip-wrapper, .recharts-default-tooltip, .recharts-active-bar, .recharts-active-shape, .recharts-tooltip-cursor, .recharts-crosshair'
          );
          tooltips.forEach((el) => {
            el.style.display = 'none';
          });

          // 2. Ensure all text and SVG elements have clean typography and solid contrast fill
          const textColor = format === 'jpeg' || !isDarkMode ? '#0f172a' : '#f8fafc';
          const textElements = clonedDoc.querySelectorAll('text, span, div');
          textElements.forEach((txt) => {
            txt.style.fontFamily = "'Inter', 'Noto Sans Tamil', sans-serif";
            txt.style.opacity = '1';
          });
          const labelListTexts = clonedDoc.querySelectorAll('.recharts-label-list text, .recharts-label, .recharts-pie-labels text');
          labelListTexts.forEach((lbl) => {
            lbl.setAttribute('fill', textColor);
            lbl.style.fill = textColor;
            lbl.style.fontWeight = '700';
            lbl.style.opacity = '1';
            lbl.style.visibility = 'visible';
            lbl.style.display = 'block';
          });

          // 3. Prepend clean title in exported image if not present
          const exportWrap = clonedDoc.querySelector('.visualization-export-wrapper');
          if (exportWrap && !exportWrap.querySelector('.export-title-banner')) {
            const titleDiv = clonedDoc.createElement('div');
            titleDiv.className = 'export-title-banner';
            titleDiv.style.fontWeight = '700';
            titleDiv.style.fontSize = '14px';
            titleDiv.style.color = isDarkMode && format !== 'jpeg' ? '#f8fafc' : '#1e293b';
            titleDiv.style.marginBottom = '8px';
            titleDiv.style.textAlign = 'left';
            titleDiv.innerText = getGraphTitle();
            exportWrap.insertBefore(titleDiv, exportWrap.firstChild);
          }
        },
      });

      const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      const imgURI = canvas.toDataURL(mimeType, 0.95);

      const titleSlug = getGraphTitle().replace(/[^a-zA-Z0-9_-]/g, '_');
      const link = document.createElement('a');
      link.download = `${titleSlug}_${graphType}.${format}`;
      link.href = imgURI;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Failed to export graph visualization:', err);
      alert('Failed to generate graph download: ' + err.message);
    }
  };

  // Derive active visualization X-Axis and Y-Axis column names
  const getVisualizationAxisColumns = () => {
    if (!datasetSchema || !datasetSchema.columns || datasetSchema.columns.length === 0) {
      return { xCol: 'வட்டம் (Taluk)', yCol: 'மதிப்பு (Value)' };
    }
    const cols = datasetSchema.columns || [];
    const xCol = cols.find((c) => c.is_taluk_column || c.is_department_column || c.data_type_detected === 'text')?.column_name || Object.keys(datasetSchema.sample_rows?.[0] || {})[0] || 'வட்டம் (Taluk)';
    const yCol = cols.find((c) => c.data_type_detected === 'number' || c.is_amount_column)?.column_name || Object.keys(datasetSchema.sample_rows?.[0] || {})[1] || 'மதிப்பு (Value)';
    return { xCol, yCol };
  };

  const { xCol: activeXCol, yCol: activeYCol } = getVisualizationAxisColumns();

  // Render ONLY ONE Chart at a time with Non-Overlapping Angled XAxis Labels and Axes Titles
  const renderSingleGraph = () => {
    const commonXAxis = (
      <XAxis
        dataKey="name"
        tick={{ fontSize: 10.5, fill: 'var(--color-text-secondary)' }}
        interval={0}
        angle={-35}
        textAnchor="end"
        height={65}
        dx={-4}
        dy={6}
      />
    );

    const commonYAxis = (
      <YAxis
        tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
        label={{
          value: activeYCol || 'மதிப்பு',
          angle: -90,
          position: 'insideLeft',
          offset: -5,
          style: { fill: 'var(--color-text-primary)', fontSize: 11, fontWeight: 700, textAnchor: 'middle' },
        }}
      />
    );

    let chartNode = null;

    const isDarkMode = document.documentElement.classList.contains('dark');
    const labelFill = isDarkMode ? '#f8fafc' : '#0f172a';

    switch (graphType) {
      case 'line':
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 25, right: 25, left: 20, bottom: 65 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              {commonXAxis}
              {commonYAxis}
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={3}
                isAnimationActive={false}
                dot={{ r: 5, fill: '#10b981', stroke: '#ffffff', strokeWidth: 1.5 }}
                activeDot={{ r: 7 }}
              >
                <LabelList
                  dataKey="value"
                  position="top"
                  offset={10}
                  fill={labelFill}
                  fontSize={11}
                  fontWeight={700}
                  formatter={(val) => (typeof val === 'number' ? val.toLocaleString('ta-IN') : val)}
                />
              </Line>
            </LineChart>
          </ResponsiveContainer>
        );
        break;

      case 'pie':
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={95}
                isAnimationActive={false}
                label={({ name, value, percent }) => `${name}: ${typeof value === 'number' ? value.toLocaleString('ta-IN') : value} (${(percent * 100).toFixed(0)}%)`}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
            </PieChart>
          </ResponsiveContainer>
        );
        break;

      case 'donut':
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={95}
                paddingAngle={3}
                isAnimationActive={false}
                label={({ name, value, percent }) => `${name}: ${typeof value === 'number' ? value.toLocaleString('ta-IN') : value} (${(percent * 100).toFixed(0)}%)`}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
            </PieChart>
          </ResponsiveContainer>
        );
        break;

      case 'scatter':
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ top: 25, right: 25, left: 20, bottom: 65 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              {commonXAxis}
              <YAxis
                dataKey="value"
                tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
                label={{
                  value: activeYCol || 'மதிப்பு',
                  angle: -90,
                  position: 'insideLeft',
                  offset: -5,
                  style: { fill: 'var(--color-text-primary)', fontSize: 11, fontWeight: 700, textAnchor: 'middle' },
                }}
              />
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
              <Scatter name="Data Distribution" data={chartData} fill="#10b981" isAnimationActive={false}>
                <LabelList
                  dataKey="value"
                  position="top"
                  offset={10}
                  fill={labelFill}
                  fontSize={11}
                  fontWeight={700}
                  formatter={(val) => (typeof val === 'number' ? val.toLocaleString('ta-IN') : val)}
                />
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        );
        break;

      case 'area':
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartData} margin={{ top: 25, right: 25, left: 20, bottom: 65 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              {commonXAxis}
              {commonYAxis}
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                fill="rgba(16, 185, 129, 0.25)"
                strokeWidth={2}
                isAnimationActive={false}
                dot={{ r: 5, fill: '#10b981', stroke: '#ffffff', strokeWidth: 1.5 }}
              >
                <LabelList
                  dataKey="value"
                  position="top"
                  offset={10}
                  fill={labelFill}
                  fontSize={11}
                  fontWeight={700}
                  formatter={(val) => (typeof val === 'number' ? val.toLocaleString('ta-IN') : val)}
                />
              </Area>
            </AreaChart>
          </ResponsiveContainer>
        );
        break;

      case 'bar':
      default:
        chartNode = (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 25, right: 25, left: 20, bottom: 65 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              {commonXAxis}
              {commonYAxis}
              <Tooltip cursor={false} contentStyle={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-surface-border)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--color-text-primary)' }} />
              <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                <LabelList
                  dataKey="value"
                  position="top"
                  offset={6}
                  fill={labelFill}
                  fontSize={11}
                  fontWeight={700}
                  formatter={(val) => (typeof val === 'number' ? val.toLocaleString('ta-IN') : val)}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
        break;
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
        {chartNode}
        {/* Dedicated Centered X-Axis Title with ZERO overlap with angled tick marks */}
        {['bar', 'line', 'area', 'scatter'].includes(graphType) && (
          <div
            style={{
              textAlign: 'center',
              fontSize: '0.82rem',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginTop: 4,
              letterSpacing: '0.02em',
            }}
          >
            {activeXCol || 'வட்டம்'}
          </div>
        )}
      </div>
    );
  };

  // Extract ONLY the 2 visualization data columns (X-Axis and Y-Axis) for table rendering
  const tableRows = datasetSchema?.sample_rows && datasetSchema.sample_rows.length > 0
    ? datasetSchema.sample_rows.map((row) => ({
      [activeXCol]: row[activeXCol] !== undefined && row[activeXCol] !== null ? String(row[activeXCol]) : (row.name || '-'),
      [activeYCol]: row[activeYCol] !== undefined && row[activeYCol] !== null ? row[activeYCol] : (row.value || '-'),
    }))
    : [
      { [activeXCol]: 'Retail', [activeYCol]: 450 },
      { [activeXCol]: 'Education', [activeYCol]: 390 },
      { [activeXCol]: 'Health Services', [activeYCol]: 310 },
      { [activeXCol]: 'Public Works', [activeYCol]: 290 },
      { [activeXCol]: 'Agriculture', [activeYCol]: 240 },
      { [activeXCol]: 'Revenue', [activeYCol]: 190 },
    ];

  const tableColumns = [activeXCol, activeYCol];


  return (
    <div
      className="animate-fade-in"
      style={{
        maxWidth: 1680,
        margin: '0 auto',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minHeight: 0,
        boxSizing: 'border-box',
      }}
    >
      {/* ERROR ALERT */}
      {error && (
        <div style={{ flexShrink: 0, marginBottom: 8, padding: 10, background: '#fee2e2', color: '#991b1b', borderRadius: 8, fontSize: '0.85rem', display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#991b1b' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* MAIN TWO-COLUMN WORKSPACE LAYOUT (STARTS AT TOP) */}
      <div
        className="data-workspace-grid"
        style={{
          flex: 1,
          minHeight: 'calc(100vh - 100px)',
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.4fr) minmax(400px, 1fr)',
          gap: 16,
          alignItems: 'stretch',
          overflow: 'hidden',
        }}
      >
        {/* ========================================================================= */}
        {/* LEFT COLUMN: DATA & VISUALIZATION WORKSPACE (WITH MODULE TITLE)           */}
        {/* ========================================================================= */}
        <div
          className="left-visualization-column"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            overflowY: 'auto',
            paddingRight: 4,
            boxSizing: 'border-box',
            minHeight: 0,
          }}
        >
          {/* Module Title Header */}
          <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 4 }}>
            <div>
              <h1 className="module-title tamil-text" style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                {t('data.title')}
              </h1>
              <p style={{ fontSize: '0.86rem', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }} className="tamil-text">
                {t('data.subtitle')}
              </p>
            </div>
          </div>
          {/* CONDITION 1: BEFORE FILE UPLOAD — VISUALLY CENTERED UPLOAD CARD */}
          {!selectedDatasetId ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px 0',
              }}
            >
              <div
                className="card"
                onClick={() => document.getElementById('data-module-upload').click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileUpload({ target: { files: e.dataTransfer.files } });
                  }
                }}
                style={{
                  width: '100%',
                  maxWidth: 520,
                  cursor: 'pointer',
                  border: '2px dashed #10b981',
                  borderRadius: 16,
                  padding: '48px 24px',
                  background: 'var(--color-surface-card)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 14,
                  textAlign: 'center',
                  boxShadow: '0 8px 30px rgba(0, 0, 0, 0.04)',
                }}
              >
                <input
                  id="data-module-upload"
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />
                <UploadCloud size={64} style={{ color: '#10b981', strokeWidth: 1.8 }} />
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  Upload Dataset
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                  Drag & Drop Your Files Here or Browse Files
                </div>
                <button
                  type="button"
                  className="btn"
                  disabled={uploading}
                  style={{
                    background: '#10b981',
                    color: '#ffffff',
                    borderRadius: 20,
                    padding: '9px 28px',
                    fontWeight: 600,
                    fontSize: '0.92rem',
                    border: 'none',
                    marginTop: 4,
                  }}
                >
                  {uploading ? 'பதிவேற்றுகிறது...' : 'Browse Files'}
                </button>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <span style={{ padding: '3px 10px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: 6, fontSize: '0.75rem', fontWeight: 600 }}>
                    CSV
                  </span>
                  <span style={{ padding: '3px 10px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: 6, fontSize: '0.75rem', fontWeight: 600 }}>
                    XLS
                  </span>
                  <span style={{ padding: '3px 10px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: 6, fontSize: '0.75rem', fontWeight: 600 }}>
                    XLSX
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* CONDITION 2: AFTER FILE UPLOAD — COMPACT DATASET INFO, SINGLE GRAPH & TABLE */
            <>
              {/* 1. CLEAN COMPACT DATASET INFORMATION HEADER */}
              <div
                className="card"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 10,
                  borderLeft: '4px solid #10b981',
                  background: 'var(--color-surface-card)',
                  borderRadius: 10,
                  flexShrink: 0,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <FileSpreadsheet size={20} style={{ color: '#10b981' }} />
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)' }}>
                    📄 {selectedDataset?.file_name || datasetSchema?.file_name || 'Dataset.csv'}
                  </span>
                  <span style={{ fontSize: '0.88rem', color: 'var(--color-text-secondary)' }}>
                    | {(datasetSchema?.row_count || selectedDataset?.row_count || 0).toLocaleString('ta-IN')} rows | {datasetSchema?.column_count || selectedDataset?.column_count || 0} columns
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button
                    className="btn-dark-pro"
                    onClick={() => document.getElementById('data-module-upload').click()}
                    style={{ gap: 4, fontSize: '0.88rem' }}
                  >
                    <Upload size={13} />
                    <span>Replace</span>
                  </button>
                  <input
                    id="data-module-upload"
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                  />
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={(e) => handleDeleteDataset(selectedDatasetId, e)}
                    style={{ color: '#ef4444', fontSize: '0.88rem', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '6px 12px', borderRadius: 8 }}
                    title="Delete Dataset"
                  >
                    <Trash2 size={13} />
                    <span>Delete</span>
                  </button>
                </div>
              </div>

              {/* 2. SINGLE GRAPH CARD WITH TOOLBAR & CONTROLS */}
              <div
                ref={graphCardRef}
                className="card graph-card-export-target"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  background: 'var(--color-surface-card)',
                  borderRadius: 12,
                  border: '1px solid var(--color-surface-border)',
                }}
              >
                {/* Graph Card Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <BarChart3 size={18} style={{ color: '#10b981' }} />
                    <span>{getGraphTitle()}</span>
                  </div>

                  {/* Top-Right Controls: Graph Type Dropdown + Download Graph Button */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {/* Graph Type Dropdown */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                        Graph Type:
                      </span>
                      <select
                        value={graphType}
                        onChange={(e) => handleGraphTypeChange(e.target.value)}
                        style={{
                          padding: '5px 12px',
                          borderRadius: 8,
                          border: '1px solid #10b981',
                          background: 'var(--color-surface-input)',
                          fontSize: '1rem',
                          fontWeight: 600,
                          color: '#10b981',
                          cursor: 'pointer',
                          outline: 'none',
                        }}
                      >
                        <option value="bar">Bar Chart</option>
                        <option value="line">Line Chart</option>
                        <option value="pie">Pie Chart</option>
                        <option value="donut">Donut Chart</option>
                        <option value="scatter">Scatter Plot</option>
                        <option value="area">Area Chart</option>
                      </select>
                    </div>

                    {/* Download Graph Dropdown */}
                    <div className="download-dropdown-container" style={{ position: 'relative' }}>
                      <button
                        className="btn-dark-pro"
                        onClick={() => setDownloadOpen(!downloadOpen)}
                        style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.88rem' }}
                      >
                        <Download size={14} />
                        <span>Download Graph</span>
                        <ChevronDown size={12} />
                      </button>

                      {downloadOpen && (
                        <div
                          style={{
                            position: 'absolute',
                            right: 0,
                            top: '100%',
                            marginTop: 4,
                            zIndex: 50,
                            background: '#1e293b',
                            border: '1px solid #334155',
                            borderRadius: 8,
                            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                            padding: '4px',
                            display: 'flex',
                            flexDirection: 'column',
                            minWidth: 120,
                          }}
                        >
                          <button
                            onClick={() => handleDownloadGraph('png')}
                            style={{
                              padding: '8px 12px',
                              textAlign: 'left',
                              background: 'transparent',
                              border: 'none',
                              color: '#f8fafc',
                              fontSize: '0.88rem',
                              fontWeight: 500,
                              cursor: 'pointer',
                              borderRadius: 4,
                            }}
                            className="hover:bg-emerald-600/30"
                          >
                            PNG Format
                          </button>
                          <button
                            onClick={() => handleDownloadGraph('jpeg')}
                            style={{
                              padding: '8px 12px',
                              textAlign: 'left',
                              background: 'transparent',
                              border: 'none',
                              color: '#f8fafc',
                              fontSize: '0.88rem',
                              fontWeight: 500,
                              cursor: 'pointer',
                              borderRadius: 4,
                            }}
                            className="hover:bg-emerald-600/30"
                          >
                            JPEG Format
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* PURE VISUALIZATION EXPORT TARGET (Chart SVG with clear axes) */}
                <div
                  ref={exportContainerRef}
                  className="visualization-export-wrapper"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--color-surface-card)',
                    borderRadius: 10,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <div ref={chartRef} style={{ width: '100%', minHeight: 330, paddingTop: 2 }}>
                    {analyzingStep ? (
                      <div style={{ height: 330, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, color: '#10b981' }}>
                        <RefreshCw size={20} className="animate-spin" />
                        <span style={{ fontSize: '1rem', fontWeight: 600 }}>Generating graph...</span>
                      </div>
                    ) : (
                      renderSingleGraph()
                    )}
                  </div>
                </div>

                {/* Graph Footer: Ask AI About This Chart Button */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 10, borderTop: '1px solid var(--color-surface-border)' }}>
                  <span style={{ fontSize: '0.88rem', color: '#10b981', fontWeight: 600 }}>
                    Active Visualization: {graphType.toUpperCase()} CHART
                  </span>

                  <button
                    onClick={handleAskAiAboutChart}
                    className="btn"
                    style={{
                      background: 'rgba(16, 185, 129, 0.12)',
                      color: '#10b981',
                      border: '1px solid #10b981',
                      borderRadius: 16,
                      padding: '6px 16px',
                      fontSize: '0.88rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <Bot size={14} />
                    <span>Ask AI About This Chart</span>
                  </button>
                </div>
              </div>

              {/* 3. DATA TABLE (BELOW GRAPH) */}
              <div
                className="card"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  background: 'var(--color-surface-card)',
                  borderRadius: 12,
                  border: '1px solid var(--color-surface-border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Table size={16} style={{ color: '#10b981' }} />
                    <span>Data Table</span>
                    <span style={{ fontSize: '0.88rem', fontWeight: 500, color: 'var(--color-text-secondary)', background: 'var(--color-surface-hover)', padding: '2px 8px', borderRadius: 12 }}>
                      Showing {tableRows.length} of {(datasetSchema?.row_count || tableRows.length).toLocaleString('ta-IN')} rows
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    maxHeight: 340,
                    overflow: 'auto',
                    borderRadius: 8,
                    border: '1px solid var(--color-surface-border)',
                  }}
                >
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '1rem',
                      textAlign: 'left',
                    }}
                  >
                    <thead>
                      <tr
                        style={{
                          position: 'sticky',
                          top: 0,
                          zIndex: 2,
                          background: 'var(--color-surface-hover)',
                          borderBottom: '2px solid var(--color-surface-border)',
                        }}
                      >
                        {tableColumns.map((col) => (
                          <th
                            key={col}
                            style={{
                              padding: '12px 16px',
                              fontWeight: 600,
                              fontSize: '0.95rem',
                              color: 'var(--color-text-primary)',
                              whiteSpace: 'nowrap',
                              maxWidth: 160,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                            title={col}
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableRows.map((row, rowIdx) => (
                        <tr
                          key={rowIdx}
                          style={{
                            borderBottom: '1px solid var(--color-surface-border)',
                            background: rowIdx % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)',
                            transition: 'background-color 0.15s ease',
                          }}
                        >
                          {tableColumns.map((col) => {
                            const val = row[col];
                            const displayVal = val === null || val === undefined ? '-' : String(val);
                            return (
                              <td
                                key={col}
                                style={{
                                  padding: '12px 16px',
                                  fontSize: '1rem',
                                  color: 'var(--color-text-secondary)',
                                  whiteSpace: 'nowrap',
                                  maxWidth: 160,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                }}
                                title={displayVal}
                              >
                                {displayVal}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>

        {/* RIGHT COLUMN: MODERN GLASSMORPHIC AI DATA ASSISTANT PANEL */}
        <div
          className="right-ai-column"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            height: 'calc(100vh - 96px)',
            minHeight: 680,
            overflow: 'hidden',
            padding: '14px 16px',
            background: 'var(--color-surface-card)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            borderRadius: 16,
            border: '1px solid rgba(16, 185, 129, 0.25)',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.04)',
            boxSizing: 'border-box',
            position: 'sticky',
            top: 0,
          }}
        >
          {/* Glass Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingBottom: 8,
              borderBottom: '1px solid var(--color-surface-border)',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.1) 100%)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#10b981',
                }}
              >
                <Bot size={16} />
              </div>
              <div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }} className="tamil-text">
                  AI Data Assistant
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginTop: 1 }}>
                  Ask questions in Tamil or English
                </div>
              </div>
            </div>

            {/* UPPER RIGHT SIDE: NEW CHAT BUTTON */}
            <button
              onClick={handleClearChat}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                padding: '4px 10px',
                borderRadius: 9999,
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                color: '#10b981',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              className="hover:bg-emerald-500/20 hover:border-emerald-500/40 tamil-text"
              title="Start a new chat session"
            >
              <Plus size={12} />
              <span>New Chat</span>
            </button>
          </div>

          {/* Messages Stream (Independent Scrollable Container) */}
          <div
            ref={chatFeedContainerRef}
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
              paddingRight: 4,
              paddingTop: 4,
              paddingBottom: 4,
            }}
          >
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '90%',
                  width: 'fit-content',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  boxSizing: 'border-box',
                }}
              >
                <div
                  style={{
                    padding: msg.sender === 'user' ? '9px 14px' : '11px 15px 9px 15px',
                    borderRadius: msg.sender === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    fontSize: '0.92rem',
                    background:
                      msg.sender === 'user'
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : 'var(--color-surface-hover)',
                    color: msg.sender === 'user' ? '#ffffff' : 'var(--color-text-primary)',
                    boxShadow:
                      msg.sender === 'user'
                        ? '0 3px 10px rgba(16, 185, 129, 0.25)'
                        : '0 2px 10px rgba(0, 0, 0, 0.04)',
                    border: msg.sender === 'user' ? 'none' : '1px solid rgba(16, 185, 129, 0.15)',
                    backdropFilter: msg.sender === 'ai' ? 'blur(8px)' : 'none',
                    boxSizing: 'border-box',
                    overflowWrap: 'anywhere',
                    wordBreak: 'break-word',
                  }}
                >
                  <div
                    style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      overflowWrap: 'anywhere',
                      lineHeight: 1.55,
                      fontSize: '0.92rem',
                    }}
                    className="tamil-text"
                  >
                    {msg.text.trim()}
                  </div>

                  {/* Timestamp & Micro Actions Footer */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginTop: 6,
                      gap: 8,
                      borderTop: msg.sender === 'ai' ? '1px solid rgba(16, 185, 129, 0.12)' : 'none',
                      paddingTop: msg.sender === 'ai' ? 6 : 0,
                      flexWrap: 'wrap',
                    }}
                  >
                    <span style={{ fontSize: '0.74rem', opacity: msg.sender === 'user' ? 0.85 : 0.65 }}>
                      {msg.timestamp}
                    </span>

                    {msg.sender === 'ai' && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <button
                          onClick={() => handleCopyMessage(msg.text, msg.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 3,
                            padding: '2px 8px',
                            borderRadius: 9999,
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            color: '#10b981',
                            fontSize: '0.74rem',
                            cursor: 'pointer',
                          }}
                          title="Copy text"
                        >
                          {copiedMessageId === msg.id ? <Check size={11} /> : <Copy size={11} />}
                          <span>{copiedMessageId === msg.id ? 'Copied' : 'Copy'}</span>
                        </button>
                        <button
                          onClick={() => handleShareMessage(msg.text)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 3,
                            padding: '2px 8px',
                            borderRadius: 9999,
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            color: '#10b981',
                            fontSize: '0.74rem',
                            cursor: 'pointer',
                          }}
                          title="Share insight"
                        >
                          <Share2 size={11} />
                          <span>Share</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {chatLoading && (
              <div
                style={{
                  alignSelf: 'flex-start',
                  padding: '10px 16px',
                  borderRadius: '20px 20px 20px 4px',
                  background: 'var(--color-surface-hover)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  fontSize: '1rem',
                  color: '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <RefreshCw size={14} className="animate-spin" />
                <span>பகுப்பாய்வு செய்யப்படுகிறது...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* FIXED BOTTOM ACTION FOOTER (STATIONARY PROMPTS + INPUT) */}
          <div
            style={{
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              paddingTop: 8,
              borderTop: '1px solid var(--color-surface-border)',
            }}
          >
            {/* RECOMMENDED PROMPTS (SLIM SIZE) */}
            {!chatMessages.some((msg) => msg.sender === 'user') && !chatInput.trim() && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 1 }}>
                  Recommended Prompts
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {generateDynamicPrompts(datasetSchema).map((prompt) => (
                    <button
                      key={prompt.id}
                      onClick={() => handleSendChatMessage(prompt.query)}
                      style={{
                        fontSize: '0.78rem',
                        fontWeight: 500,
                        padding: '5px 12px',
                        borderRadius: 8,
                        border: '1px solid rgba(16, 185, 129, 0.25)',
                        background: 'var(--color-surface-hover)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        color: 'var(--color-text-primary)',
                        textAlign: 'left',
                        width: '100%',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                      className="hover:border-emerald-500 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/30"
                      title={prompt.query}
                    >
                      <span style={{ fontSize: '0.85rem' }}>{prompt.icon}</span>
                      <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{prompt.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* FLOATING ROUNDED PILL INPUT DOCK & VOICE CONTROLS (VERTICALLY CENTERED) */}
            <div
              style={{
                flexShrink: 0,
                marginTop: 2,
                padding: '4px 6px 4px 12px',
                borderRadius: chatInput.length > 45 || chatInput.indexOf('\n') !== -1 ? 14 : 9999,
                background: 'var(--color-surface-input)',
                border: '1.5px solid rgba(16, 185, 129, 0.35)',
                boxShadow: '0 4px 16px rgba(16, 185, 129, 0.08)',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                minHeight: 40,
                boxSizing: 'border-box',
                transition: 'border-radius 0.2s ease',
              }}
            >
              <textarea
                ref={chatInputRef}
                rows={1}
                value={chatInput}
                onChange={(e) => {
                  setChatInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendChatMessage();
                    if (chatInputRef.current) {
                      chatInputRef.current.style.height = '22px';
                    }
                  }
                }}
                placeholder="தரவு பற்றி கேளுங்கள்... / Ask about your data..."
                className="chat-input tamil-text"
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  fontSize: '0.9rem',
                  color: 'var(--color-text-primary)',
                  fontFamily: "'Noto Sans Tamil', 'Inter', sans-serif",
                  resize: 'none',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word',
                  overflowY: 'auto',
                  height: '22px',
                  maxHeight: '100px',
                  lineHeight: '22px',
                  padding: '1px 0',
                  margin: 0,
                }}
              />

              {/* Circular Voice Input Button */}
              <button
                onClick={toggleListening}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: isListening ? '1.5px solid #ef4444' : '1px solid rgba(16, 185, 129, 0.3)',
                  background: isListening ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.1)',
                  color: isListening ? '#ef4444' : '#10b981',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  flexShrink: 0,
                }}
                title={isListening ? 'Stop Listening' : t('common.voice_input')}
              >
                {isListening ? <MicOff size={16} className="animate-pulse" /> : <Mic size={16} />}
              </button>

              {/* Circular Send Button */}
              <button
                onClick={() => handleSendChatMessage()}
                disabled={!chatInput.trim() || chatLoading}
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: '50%',
                  background: !chatInput.trim() || chatLoading ? 'var(--color-surface-hover)' : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: !chatInput.trim() || chatLoading ? 'var(--color-text-muted)' : '#ffffff',
                  border: 'none',
                  cursor: !chatInput.trim() || chatLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: !chatInput.trim() || chatLoading ? 'none' : '0 4px 12px rgba(16, 185, 129, 0.4)',
                  transition: 'all 0.2s ease',
                  flexShrink: 0,
                }}
                title="Send message"
              >
                <Send size={15} style={{ marginLeft: 2 }} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
