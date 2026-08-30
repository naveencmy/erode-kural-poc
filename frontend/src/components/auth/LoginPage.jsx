import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import TnEmblem from '../icons/TnEmblem';
import './LoginPage.css';
import {
  ShieldCheck,
  Lock,
  Eye,
  EyeOff,
  UserCheck,
  Globe,
  Shield,
  CheckCircle2,
  Server,
  AlertCircle,
  Info,
  ChevronRight,
  Loader2,
} from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const { i18n } = useTranslation();

  // Form states
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Micro-interaction state for verification preview
  // 'idle' | 'verifying' | 'verified' | 'loading'
  const [verificationState, setVerificationState] = useState('idle');

  const currentLang = i18n.language || 'ta';
  const isTamil = currentLang === 'ta';

  const handleLanguageChange = (lang) => {
    i18n.changeLanguage(lang);
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!employeeId.trim()) {
      setErrorMessage(
        isTamil
          ? 'தயவுசெய்து உங்கள் அலுவலர் அடையாள எண்ணை உள்ளிடவும்'
          : 'Please enter your Employee ID'
      );
      return;
    }
    if (!password.trim()) {
      setErrorMessage(
        isTamil
          ? 'தயவுசெய்து உங்கள் கடவுச்சொல்லை உள்ளிடவும்'
          : 'Please enter your Password'
      );
      return;
    }

    setErrorMessage('');
    setVerificationState('verifying');

    setTimeout(() => {
      setVerificationState('verified');
      setTimeout(() => {
        setVerificationState('loading');
        setTimeout(() => {
          if (onLoginSuccess) {
            onLoginSuccess(employeeId);
          } else {
            setVerificationState('idle');
          }
        }, 800);
      }, 700);
    }, 900);
  };

  return (
    <div className="login-page-root">
      {/* Top Accent Bar */}
      <div className="login-top-accent-bar" />

      {/* Ambient Lighting & Minimal Grid Background */}
      <div className="login-bg-ambient" aria-hidden="true">
        <div className="login-bg-glow-left" />
        <div className="login-bg-glow-right" />
        <div className="login-bg-fine-grid" />
      </div>

      {/* Main Centered 2-Column Container */}
      <main className="login-main-container">
        
        {/* =======================================================
            LEFT BRAND SECTION (max-width: 640px)
            ======================================================= */}
        <section className="login-brand-section">
          
          {/* Government Brand Header */}
          <div className="gov-brand-header">
            <div className="gov-emblem-seal">
              <TnEmblem size={58} />
            </div>
            <div className="gov-brand-titles">
              <div className="gov-header-tag">
                {isTamil ? 'தமிழ்நாடு அரசு' : 'Government of Tamil Nadu'}
              </div>
              <div className="gov-header-sub">
                {isTamil ? 'அதிகாரப்பூர்வ நிர்வாக தளம்' : 'Official Administrative Portal'}
              </div>
            </div>
          </div>

          {/* Collectorate Name */}
          <div className="collectorate-title-group">
            <div className="collectorate-name-en">
              Erode District Collectorate
            </div>
            <div className="collectorate-name-ta">
              ஈரோடு மாவட்ட ஆட்சியரகம்
            </div>
          </div>

          {/* AI Product Title */}
          <div className="ai-product-group">
            <h1 className="ai-product-title-en">
              AI Administrative <span className="gold-text">Assistant</span>
            </h1>
            <div className="ai-product-title-ta">
              AI நிர்வாகப் பணிமனை
            </div>
          </div>

          {/* Tagline */}
          <div className="brand-tagline">
            <span className="highlight">Secure</span> • 
            <span className="highlight">Local</span> • 
            <span className="highlight">Intelligent</span> Administration
          </div>

          {/* Supporting Description */}
          <p className="brand-description">
            {isTamil
              ? 'மாவட்ட நிர்வாகப் பணிகளுக்கான பாதுகாப்பான, உள்ளக AI கட்டமைப்பு. அதிகாரப்பூர்வ கோப்புகள், தரவு பகுப்பாய்வு மற்றும் அரசு ஆவணங்களுக்கான பிரத்யேக நிர்வாக தளம்.'
              : 'Official air-gapped AI workspace built for the Erode District Administration. Providing secure on-premise document synthesis, departmental data analytics, and verified workflow automation.'}
          </p>

          {/* Simplified Status Bar */}
          <div className="status-bar-container">
            <div className="status-line-item">
              <span className="status-green-dot" />
              <span>
                {isTamil
                  ? 'உள்ளக AI கட்டமைப்பு • பாதுகாக்கப்பட்ட பணியிடம்'
                  : 'Local AI Infrastructure • Protected Workspace'}
              </span>
            </div>
            <div className="status-chip-badge">
              <ShieldCheck size={13} />
              <span>Air-Gapped Ready</span>
            </div>
          </div>

          {/* 3 Equal Feature Cards */}
          <div className="feature-cards-row">
            {/* Feature 1 */}
            <div className="feature-card-item">
              <div className="feature-card-icon-wrap">
                <Server size={18} />
              </div>
              <div>
                <div className="feature-card-title">
                  {isTamil ? 'உள்ளக தரவு செயலாக்கம்' : 'Secure Local Processing'}
                </div>
                <div className="feature-card-sub">
                  {isTamil ? 'முழுமையான உள்ளக இயக்கம்' : 'On-premise AI execution'}
                </div>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="feature-card-item">
              <div className="feature-card-icon-wrap">
                <Globe size={18} />
              </div>
              <div>
                <div className="feature-card-title">
                  {isTamil ? 'இருமொழி நிர்வாகம்' : 'Bilingual Administration'}
                </div>
                <div className="feature-card-sub">
                  {isTamil ? 'தமிழ் & ஆங்கில செயலாக்கம்' : 'Native Tamil & English'}
                </div>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="feature-card-item">
              <div className="feature-card-icon-wrap">
                <Shield size={18} />
              </div>
              <div>
                <div className="feature-card-title">
                  {isTamil ? 'அங்கீகரிக்கப்பட்ட அணுகல்' : 'Verified Officer Access'}
                </div>
                <div className="feature-card-sub">
                  {isTamil ? 'அலுவல் தணிக்கை நெறிமுறைகள்' : 'Role-governed audit trail'}
                </div>
              </div>
            </div>
          </div>

        </section>

        {/* =======================================================
            RIGHT LOGIN PANEL (Spacious elevated card)
            ======================================================= */}
        <section className="login-panel-section">
          <div className="login-card-container">
            
            {/* Top Bar: Official Portal & Segmented Language Control */}
            <div className="login-card-topbar">
              <div className="portal-tag-badge">
                <ShieldCheck size={16} className="text-[#c8a951]" />
                <span>{isTamil ? 'அதிகாரப்பூர்வ உள்நுழைவு' : 'Official Access Portal'}</span>
              </div>

              <div className="lang-toggle-control">
                <button
                  type="button"
                  className={`lang-toggle-btn ${!isTamil ? 'active' : ''}`}
                  onClick={() => handleLanguageChange('en')}
                >
                  English
                </button>
                <button
                  type="button"
                  className={`lang-toggle-btn ${isTamil ? 'active' : ''}`}
                  onClick={() => handleLanguageChange('ta')}
                >
                  தமிழ்
                </button>
              </div>
            </div>

            {/* Welcome Section */}
            <div className="login-welcome-group">
              <h2 className="login-welcome-title">
                {isTamil ? 'உள்நுழைவு' : 'Welcome Back'}
              </h2>
              <div className="login-welcome-sub-en">
                {isTamil
                  ? 'ஈரோடு மாவட்ட ஆட்சியரக நிர்வாக பணிமனை'
                  : 'Sign in to the Erode District Collectorate Administrative Workspace'}
              </div>
              <div className="login-welcome-sub-ta">
                அங்கீகரிக்கப்பட்ட அலுவலர்களுக்கான பாதுகாப்பான உள்நுழைவு
              </div>
            </div>

            {/* Error Notification */}
            {errorMessage && (
              <div style={{
                marginBottom: '16px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(153, 27, 27, 0.4)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#fecaca',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="login-form-body">
              
              {/* Employee ID */}
              <div className="login-field-group">
                <div className="login-field-header">
                  <label htmlFor="employee-id-input" className="login-field-label">
                    {isTamil ? 'அலுவலர் அடையாள எண்' : 'Employee ID'}
                  </label>
                  <span className="login-field-hint">
                    Example: ERD-XXX-000
                  </span>
                </div>

                <div className="login-input-relative">
                  <UserCheck size={18} className="login-input-lead-icon" />
                  <input
                    id="employee-id-input"
                    type="text"
                    className="login-input-box"
                    placeholder={isTamil ? 'அலுவலர் அடையாள எண்ணை உள்ளிடவும்' : 'Enter official employee ID'}
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value.toUpperCase())}
                    disabled={verificationState !== 'idle'}
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div className="login-field-group">
                <div className="login-field-header">
                  <label htmlFor="password-input" className="login-field-label">
                    {isTamil ? 'கடவுச்சொல்' : 'Password'}
                  </label>
                </div>

                <div className="login-input-relative">
                  <Lock size={18} className="login-input-lead-icon" />
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    className="login-input-box with-right-btn"
                    placeholder={isTamil ? 'கடவுச்சொல்லை உள்ளிடவும்' : 'Enter your password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={verificationState !== 'idle'}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="login-eye-btn"
                    title={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Remember / Forgot Password Row */}
              <div className="login-options-row">
                <label className="remember-label">
                  <input
                    type="checkbox"
                    className="remember-checkbox"
                    checked={rememberDevice}
                    onChange={(e) => setRememberDevice(e.target.checked)}
                    disabled={verificationState !== 'idle'}
                  />
                  <span>{isTamil ? 'இந்த சாதனத்தை நினைவில் கொள்க' : 'Remember this device'}</span>
                </label>

                <button
                  type="button"
                  className="forgot-pwd-btn"
                  onClick={() => {
                    alert(
                      isTamil
                        ? 'கடவுச்சொல் மீட்டமைக்க மாவட்ட ஆட்சியரக கணினி பிரிவை (System Admin) அணுகவும்.'
                        : 'Please contact the District Collectorate System Administrator for password reset assistance.'
                    );
                  }}
                >
                  {isTamil ? 'கடவுச்சொல் மறந்துவிட்டதா?' : 'Forgot password?'}
                </button>
              </div>

              {/* Role Message Callout */}
              <div className="role-callout-box">
                <Info size={16} className="role-callout-icon" />
                <span>
                  {isTamil
                    ? 'சரிபார்ப்புக்குப் பின் பணிக்கான பணியிடம் ஒதுக்கப்படும்'
                    : 'Role-based workspace will be assigned after verification'}
                </span>
              </div>

              {/* Primary Action Button */}
              <button
                type="submit"
                className="login-submit-btn"
                disabled={verificationState !== 'idle'}
              >
                {verificationState === 'idle' && (
                  <>
                    <ShieldCheck size={19} className="text-[#f1cf6b]" />
                    <span>{isTamil ? 'பாதுகாப்பாக உள்நுழைக' : 'Secure Sign In'}</span>
                    <ChevronRight size={18} className="text-[#c8a951]" />
                  </>
                )}

                {verificationState === 'verifying' && (
                  <>
                    <Loader2 size={18} className="spin-icon text-amber-300" />
                    <span>{isTamil ? 'அடையாளம் சரிபார்க்கப்படுகிறது...' : 'Verifying identity...'}</span>
                  </>
                )}

                {verificationState === 'verified' && (
                  <>
                    <CheckCircle2 size={19} className="text-emerald-400" />
                    <span className="text-emerald-300">
                      {isTamil ? 'அலுவலர் சரிபார்க்கப்பட்டது' : 'Officer verified'}
                    </span>
                  </>
                )}

                {verificationState === 'loading' && (
                  <>
                    <Loader2 size={18} className="spin-icon text-emerald-400" />
                    <span>{isTamil ? 'பணிமனை ஏற்றப்படுகிறது...' : 'Loading authorized workspace...'}</span>
                  </>
                )}
              </button>

            </form>

            {/* Security Notice Section */}
            <div className="login-security-notice">
              <Shield size={16} className="security-badge-icon" />
              <div>
                <div className="security-notice-title">
                  {isTamil ? 'அங்கீகரிக்கப்பட்ட அரசு அலுவலர்கள் மட்டும்' : 'Authorized Government Personnel Only'}
                </div>
                <div className="security-notice-desc">
                  {isTamil
                    ? 'இவ்வமைப்பின் பயன்பாடு நிர்வாக பாதுகாப்பு மற்றும் தணிக்கை நோக்கங்களுக்காக கண்காணிக்கப்படுகிறது.'
                    : 'Access is monitored and recorded for administrative security and audit purposes.'}
                </div>
              </div>
            </div>

          </div>
        </section>

      </main>

      {/* Minimal Government Page Footer */}
      <footer className="login-page-footer">
        <div className="footer-left">
          {isTamil ? 'ஈரோடு மாவட்ட ஆட்சியரகம் • தமிழ்நாடு அரசு' : 'Erode District Collectorate • Government of Tamil Nadu'}
        </div>
        <div className="footer-right">
          {isTamil ? 'பாதுகாப்பான உள்ளக AI நிர்வாக தளம்' : 'Secure Local AI Administrative Platform'}
        </div>
      </footer>

    </div>
  );
}
