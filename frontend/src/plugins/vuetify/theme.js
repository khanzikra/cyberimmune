// CyberImmune Theme - Humanized Cybersecurity Aesthetic
// Inspired by Materio but with our own personality

export const themes = {
  light: {
    dark: false,
    colors: {
      // Primary - Electric Cyan (trust, tech, clarity)
      'primary': '#06B6D4',
      'on-primary': '#030712',
      'primary-darken-1': '#0891B2',
      'primary-lighten-1': '#22D3EE',
      
      // Secondary - Emerald Teal (security, verification)
      'secondary': '#14B8A6',
      'on-secondary': '#030712',
      'secondary-darken-1': '#0D9488',
      'secondary-lighten-1': '#2DD4BF',
      
      // Success - Green (verified, safe)
      'success': '#10B981',
      'on-success': '#030712',
      'success-darken-1': '#059669',
      
      // Warning - Amber (needs review)
      'warning': '#F59E0B',
      'on-warning': '#030712',
      'warning-darken-1': '#D97706',
      
      // Error - Red (failed, threat)
      'error': '#EF4444',
      'on-error': '#F8FAFC',
      'error-darken-1': '#DC2626',
      
      // Info - Sky Blue (info, context)
      'info': '#38BDF8',
      'on-info': '#030712',
      'info-darken-1': '#0EA5E9',
      
      // Background & Surface - Deep Navy (immersive, focused)
      'background': '#030712',
      'on-background': '#F1F5F9',
      'surface': '#0F172A',
      'on-surface': '#E2E8F0',
      'surface-variant': '#1E293B',
      'on-surface-variant': '#94A3B8',
      
      // Greys - Carefully crafted for depth
      'grey-50': '#030712',
      'grey-100': '#0F172A',
      'grey-200': '#1E293B',
      'grey-300': '#334155',
      'grey-400': '#475569',
      'grey-500': '#64748B',
      'grey-600': '#94A3B8',
      'grey-700': '#CBD5E1',
      'grey-800': '#E2E8F0',
      'grey-900': '#F1F5F9',
      
      // UI Essentials
      'perfect-scrollbar-thumb': '#334155',
      'skin-bordered-background': '#1E293B',
      'skin-bordered-surface': '#1E293B',
      'expansion-panel-text-custom-bg': '#111827',
      'track-bg': '#334155',
      'chat-bg': '#0F172A',
    },
    variables: {
      'code-color': '#22D3EE',
      'overlay-scrim-background': '#030712',
      'tooltip-background': '#1E293B',
      'overlay-scrim-opacity': 0.6,
      'hover-opacity': 0.06,
      'focus-opacity': 0.12,
      'selected-opacity': 0.1,
      'activated-opacity': 0.16,
      'pressed-opacity': 0.14,
      'dragged-opacity': 0.1,
      'disabled-opacity': 0.38,
      'border-color': '#334155',
      'border-opacity': 0.15,
      'table-header-color': '#1E293B',
      'high-emphasis-opacity': 0.92,
      'medium-emphasis-opacity': 0.68,
      'disabled-opacity': 0.42,
      
      // Shadows - Layered depth
      'shadow-key-umbra-color': '#000000',
      'shadow-key-penumbra-color': '#000000',
      'shadow-key-ambient-color': '#000000',
      'shadow-xs-opacity': 0.08,
      'shadow-sm-opacity': 0.12,
      'shadow-md-opacity': 0.16,
      'shadow-lg-opacity': 0.2,
      'shadow-xl-opacity': 0.24,
    },
  },
  
  dark: {
    dark: true,
    colors: {
      // Primary - Electric Cyan (vibrant on dark)
      'primary': '#06B6D4',
      'on-primary': '#030712',
      'primary-darken-1': '#0891B2',
      'primary-lighten-1': '#67E8F9',
      
      // Secondary - Emerald Teal
      'secondary': '#14B8A6',
      'on-secondary': '#030712',
      'secondary-darken-1': '#0D9488',
      'secondary-lighten-1': '#5EEAD4',
      
      // Success - Green
      'success': '#10B981',
      'on-success': '#030712',
      'success-darken-1': '#059669',
      
      // Warning - Amber
      'warning': '#F59E0B',
      'on-warning': '#030712',
      'warning-darken-1': '#D97706',
      
      // Error - Red (softer on dark)
      'error': '#F87171',
      'on-error': '#030712',
      'error-darken-1': '#EF4444',
      
      // Info - Sky
      'info': '#38BDF8',
      'on-info': '#030712',
      'info-darken-1': '#0EA5E9',
      
      // Background & Surface - Deep, rich navy
      'background': '#030712',
      'on-background': '#F1F5F9',
      'surface': '#0F172A',
      'on-surface': '#F1F5F9',
      'surface-variant': '#1E293B',
      'on-surface-variant': '#94A3B8',
      
      // Greys - Warm dark greys
      'grey-50': '#030712',
      'grey-100': '#0F172A',
      'grey-200': '#1E293B',
      'grey-300': '#334155',
      'grey-400': '#475569',
      'grey-500': '#64748B',
      'grey-600': '#94A3B8',
      'grey-700': '#CBD5E1',
      'grey-800': '#E2E8F0',
      'grey-900': '#F1F5F9',
      
      // UI Essentials
      'perfect-scrollbar-thumb': '#334155',
      'skin-bordered-background': '#1E293B',
      'skin-bordered-surface': '#1E293B',
      'expansion-panel-text-custom-bg': '#111827',
      'track-bg': '#334155',
      'chat-bg': '#0F172A',
    },
    variables: {
      'code-color': '#22D3EE',
      'overlay-scrim-background': '#030712',
      'tooltip-background': '#1E293B',
      'overlay-scrim-opacity': 0.7,
      'hover-opacity': 0.08,
      'focus-opacity': 0.14,
      'selected-opacity': 0.12,
      'activated-opacity': 0.18,
      'pressed-opacity': 0.16,
      'dragged-opacity': 0.12,
      'disabled-opacity': 0.4,
      'border-color': '#334155',
      'border-opacity': 0.18,
      'table-header-color': '#1E293B',
      'high-emphasis-opacity': 0.95,
      'medium-emphasis-opacity': 0.72,
      'disabled-opacity': 0.44,
      
      // Shadows - Rich, layered
      'shadow-key-umbra-color': '#000000',
      'shadow-key-penumbra-color': '#000000',
      'shadow-key-ambient-color': '#000000',
      'shadow-xs-opacity': 0.12,
      'shadow-sm-opacity': 0.16,
      'shadow-md-opacity': 0.2,
      'shadow-lg-opacity': 0.24,
      'shadow-xl-opacity': 0.3,
    },
  },
}

export default themes