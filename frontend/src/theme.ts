export const A = {
  bg: '#FAFAF8',
  surface: '#FFFFFF',
  surfaceAlt: '#F4F4F0',
  border: '#E8E8E4',
  borderLight: '#F0F0EC',
  text: '#1A1A2E',
  textSoft: '#64648C',
  textMuted: '#9898B0',
  indigo: '#5B5FF6',
  indigoLight: '#EDEDFE',
  indigoDark: '#4648C8',
  coral: '#FF6B6B',
  coralLight: '#FFF0F0',
  emerald: '#10B981',
  emeraldLight: '#ECFDF5',
  amber: '#F59E0B',
  amberLight: '#FFFBEB',
  violet: '#8B5CF6',
  violetLight: '#F5F3FF',
}

export const PILLARS: Record<string, { color: string; bg: string; icon: string }> = {
  Educate: { color: A.indigo, bg: A.indigoLight, icon: '📚' },
  Engage: { color: A.coral, bg: A.coralLight, icon: '💬' },
  Promote: { color: A.amber, bg: A.amberLight, icon: '📣' },
  Connect: { color: A.emerald, bg: A.emeraldLight, icon: '🤝' },
}

// Platform config is centralized in platformRegistry.ts — re-export for backwards compat
export { PLATFORMS, getPlatform } from './platformRegistry'
