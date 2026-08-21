import React from 'react';
import { useTranslation } from 'react-i18next';
import useAppStore from '../../stores/appStore';
import TnEmblem from '../icons/TnEmblem';
import { cn } from '../../lib/utils';
import {
  MessageSquare,
  BarChart3,
  Stamp,
  Inbox,
  Settings,
  ClipboardList,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Mail,
} from 'lucide-react';

const NAV_MODULES = [
  { id: 'general', icon: MessageSquare },
  { id: 'data', icon: BarChart3 },
  { id: 'content', icon: Stamp },
  { id: 'bulk', icon: Inbox },
  { id: 'mail', icon: Mail },
];


const NAV_BOTTOM = [
  { id: 'audit', icon: ClipboardList },
  { id: 'settings', icon: Settings },
];

export default function Sidebar() {
  const { t } = useTranslation();
  const {
    currentModule,
    setCurrentModule,
    sidebarCollapsed,
    toggleSidebar,
  } = useAppStore();

  return (
    <aside className={cn('sidebar', sidebarCollapsed && 'collapsed')}>
      {/* Header with emblem */}
      <div
        style={{
          padding: sidebarCollapsed ? '20px 12px' : '20px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          minHeight: 80,
        }}
      >
        <div
          style={{
            background: '#ffffff',
            borderRadius: '50%',
            padding: '3px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <TnEmblem size={sidebarCollapsed ? 30 : 36} />
        </div>
        {!sidebarCollapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div
              className="tamil-text"
              style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: '#c8a951',
                whiteSpace: 'nowrap',
              }}
            >
              {t('app_title')}
            </div>
            <div
              style={{
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.5)',
                marginTop: 2,
              }}
            >
              {t('app_subtitle')}
            </div>
          </div>
        )}
      </div>

      {/* Module Navigation */}
      <nav style={{ flex: 1, paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV_MODULES.map((mod) => {
          const Icon = mod.icon;
          const isActive = currentModule === mod.id;
          return (
            <button
              key={mod.id}
              className={cn('nav-item', isActive && 'active')}
              onClick={() => setCurrentModule(mod.id)}
              title={t(`sidebar.${mod.id}`)}
            >
              <Icon size={20} style={{ flexShrink: 0 }} />
              {!sidebarCollapsed && (
                <span className="nav-label tamil-text">{t(`sidebar.${mod.id}`)}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div
        style={{
          borderTop: '1px solid rgba(255,255,255,0.1)',
          paddingTop: 8,
          paddingBottom: 16,
        }}
      >
        {NAV_BOTTOM.map((mod) => {
          const Icon = mod.icon;
          return (
            <button
              key={mod.id}
              className="nav-item"
              onClick={() => setCurrentModule(mod.id)}
              title={t(`sidebar.${mod.id}`)}
            >
              <Icon size={20} style={{ flexShrink: 0 }} />
              {!sidebarCollapsed && (
                <span className="nav-label tamil-text">{t(`sidebar.${mod.id}`)}</span>
              )}
            </button>
          );
        })}

        {/* Collapse toggle */}
        <button
          className="nav-item"
          onClick={toggleSidebar}
          title={sidebarCollapsed ? 'Expand' : 'Collapse'}
          style={{ marginTop: 4 }}
        >
          {sidebarCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
          {!sidebarCollapsed && <span className="nav-label">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
