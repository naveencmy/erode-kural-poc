import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import TnEmblem from '../icons/TnEmblem';
import { Sun, Moon, Bell, Globe, User } from 'lucide-react';

export default function TopBar() {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme, officerId, setOfficerId } = useAppStore();
  const [showOfficerInput, setShowOfficerInput] = useState(false);

  const toggleLang = () => {
    const next = i18n.language === 'ta' ? 'en' : 'ta';
    i18n.changeLanguage(next);
  };

  return (
    <header
      style={{
        background: 'linear-gradient(90deg, #ea580c 0%, #f97316 40%, #fb923c 100%)',
        color: '#ffffff',
        height: '56px',
        padding: '0 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 8px rgba(234, 88, 12, 0.25)',
        zIndex: 20,
        position: 'sticky',
        top: 0,
      }}
    >
      {/* Left: Emblem + Collectorate Branding */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div
          style={{
            background: '#ffffff',
            borderRadius: '50%',
            padding: '2px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <TnEmblem size={34} isFullColor={true} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span
            className="tamil-text"
            style={{
              fontSize: '0.92rem',
              fontWeight: 800,
              color: '#ffffff',
              lineHeight: 1.2,
              letterSpacing: '0.2px',
            }}
          >
            ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம்
          </span>
          <span
            style={{
              fontSize: '0.68rem',
              color: 'rgba(255, 255, 255, 0.88)',
              fontWeight: 500,
              lineHeight: 1,
            }}
          >
            AI உதவி அமைப்பு • Erode District Collectorate
          </span>
        </div>
      </div>

      {/* Right: Actions (Language, Theme, Notification, Officer) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Language Toggle */}
        <button
          className="btn"
          onClick={toggleLang}
          title="மொழி மாற்று (Toggle Language)"
          style={{
            background: 'rgba(255, 255, 255, 0.18)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            color: '#ffffff',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            cursor: 'pointer',
          }}
        >
          <Globe size={14} />
          <span>{i18n.language === 'ta' ? 'EN' : 'தமிழ்'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          className="btn"
          onClick={toggleTheme}
          title={t('topbar.theme_toggle')}
          style={{
            background: 'rgba(255, 255, 255, 0.18)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            color: '#ffffff',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Notifications */}
        <button
          className="btn"
          title={t('topbar.notifications')}
          style={{
            background: 'rgba(255, 255, 255, 0.18)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            color: '#ffffff',
            padding: '6px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <Bell size={15} />
        </button>

        {/* Officer Profile Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '4px 12px',
            background: '#ffffff',
            color: '#1a3a5c',
            borderRadius: '20px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '0.8rem',
          }}
          onClick={() => setShowOfficerInput(!showOfficerInput)}
          title="அலுவலர் விவரம் (Officer Profile)"
        >
          <div
            style={{
              width: 20,
              height: 20,
              borderRadius: '50%',
              background: 'rgba(234, 88, 12, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ea580c',
            }}
          >
            <User size={13} />
          </div>
          {showOfficerInput ? (
            <input
              autoFocus
              value={officerId}
              onChange={(e) => setOfficerId(e.target.value)}
              onBlur={() => setShowOfficerInput(false)}
              onKeyDown={(e) => e.key === 'Enter' && setShowOfficerInput(false)}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                width: 70,
                fontSize: '0.8rem',
                color: '#1a3a5c',
                fontWeight: 700,
              }}
            />
          ) : (
            <span>{officerId === 'OFC001' ? 'Ram' : officerId}</span>
          )}
        </div>
      </div>
    </header>
  );
}
