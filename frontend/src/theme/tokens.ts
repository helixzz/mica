// Mica Design Tokens — single source of truth for visual identity.
// See docs/DESIGN.md for full rationale, usage rules, and the 5 iron rules.
// AGENTS.md §5.8 references this file. Do not hardcode hex values elsewhere.

export const tokens = {
  color: {
    // Brand: Otter Brown — single accent. Allowed only for primary CTA, selected
    // nav, tab indicator, chart primary metric, and `state.progress`.
    // See docs/DESIGN.md §2.① for the full discipline.
    primary: {
      50: '#F8F4F1',
      100: '#EBE1D8',
      200: '#D8C3B1',
      300: '#C4A48A',
      400: '#B18563',
      500: '#8B5E3C',
      600: '#704B30',
      700: '#543824',
      800: '#382518',
      900: '#1C130C',
    },
    // Neutral: warm-tinted scale paired with Otter Brown.
    // 25 (Paper Beige) and 250 (Hairline Beige) introduced in v1.39.0.
    neutral: {
      0: '#FFFFFF', // Pure White — card surface
      25: '#FAFAF8', // ★ Paper Beige — page canvas
      50: '#F7F6F5', // Subtle Beige — card-internal section
      100: '#EFECE9', // Sunken
      200: '#DFDBD7',
      250: '#E8E4DF', // ★ Hairline Beige — primary 1px border
      300: '#CFCAC5',
      400: '#AFA9A3',
      500: '#8F8881', // Slate — tertiary text
      600: '#6F6861', // Steel — placeholder
      700: '#4F4943', // Graphite — secondary text
      800: '#2F2B27', // Carbon
      900: '#1F1C19', // Ink — primary text
      950: '#0F0E0D',
    },
    // Legacy semantic palettes — retained because v1.38- code references
    // tokens.color.success.500 etc. New code MUST prefer tokens.color.state.*
    // which carries the canonical semantics. See docs/DESIGN.md §3.3.
    success: {
      50: '#F0FDF4',
      500: '#22C55E',
      700: '#15803D',
    },
    warning: {
      50: '#FFFBEB',
      500: '#F59E0B',
      700: '#B45309',
    },
    error: {
      50: '#FEF2F2',
      500: '#EF4444',
      700: '#B91C1C',
    },
    info: {
      50: '#EFF6FF',
      500: '#3B82F6',
      700: '#1D4ED8',
    },
    // ★ State Tokens (v1.39.0+) — the canonical 6-color semantic palette.
    // All business statuses must map to exactly one of these.
    // `progress` intentionally reuses Otter Brown — "in-progress" is Mica's
    // most common state, so binding it to brand color strengthens identity.
    state: {
      info: { 50: '#EFF6FF', 200: '#BFDBFE', 500: '#3B82F6', 700: '#1D4ED8' },
      progress: { 50: '#F8F4F1', 200: '#D8C3B1', 500: '#8B5E3C', 700: '#543824' },
      success: { 50: '#F0FDF4', 200: '#BBF7D0', 500: '#22C55E', 700: '#15803D' },
      warning: { 50: '#FFFBEB', 200: '#FDE68A', 500: '#F59E0B', 700: '#B45309' },
      error: { 50: '#FEF2F2', 200: '#FECACA', 500: '#EF4444', 700: '#B91C1C' },
      neutral: { 50: '#F7F6F5', 200: '#DFDBD7', 500: '#8F8881', 700: '#4F4943' },
    },
    // ★ Data Viz Palette (v1.39.0+) — Recharts/SVG fills/strokes must use only
    // these. All desaturated to coexist with Otter Brown on Paper Beige.
    dataViz: {
      primary: '#8B5E3C',
      secondary: '#C4A48A',
      positive: '#2F8F69',
      attention: '#C97B3F',
      critical: '#B85450',
      baseline: '#6F6861',
    },
    surface: {
      light: {
        bg: '#FAFAF8', // ★ Paper Beige
        subtle: '#F7F6F5',
        elevated: '#FFFFFF',
        sunken: '#EFECE9',
      },
      dark: {
        bg: '#161514', // ★ warm Onyx
        subtle: '#1A1816',
        elevated: '#1F1D1B',
        sunken: '#0F0E0D',
      },
    },
    text: {
      light: {
        primary: '#1F1C19',
        secondary: '#4F4943',
        tertiary: '#8F8881',
        disabled: '#CFCAC5',
        inverse: '#FFFFFF',
      },
      dark: {
        primary: '#F7F6F5',
        secondary: '#D5D0CB',
        tertiary: '#9E9790',
        disabled: '#4F4943',
        inverse: '#0F0E0D',
      },
    },
    border: {
      light: {
        hairline: '#E8E4DF', // ★ primary 1px border
        subtle: '#EFECE9',
        default: '#DFDBD7',
        strong: '#AFA9A3',
      },
      dark: {
        hairline: '#2F2B27', // ★ primary 1px border in dark mode
        subtle: '#26221F',
        default: '#3A3632',
        strong: '#5A544E',
      },
    },
  },
  space: {
    0: 0,
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 24,
    6: 32,
    7: 48,
    8: 64,
    9: 96,
  },
  // 4 fixed values per docs/DESIGN.md §5.1. Do not introduce 6 / 10 / 14 / 16 / 20.
  radius: {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,
    xl: 12,
    full: 9999,
  },
  // ★ Brand-tinted shadows (v1.39.0+) — all use rgba(139, 94, 60, ...)
  // micro-tinting instead of pure black, so elevation reads as on-brand.
  shadow: {
    xs: '0 1px 2px 0 rgba(139, 94, 60, 0.04)',
    sm: '0 1px 2px 0 rgba(139, 94, 60, 0.04)',
    md: '0 2px 6px 0 rgba(139, 94, 60, 0.08), 0 1px 2px 0 rgba(139, 94, 60, 0.04)',
    lg: '0 4px 12px 0 rgba(139, 94, 60, 0.08), 0 1px 3px 0 rgba(139, 94, 60, 0.04)',
    xl: '0 16px 48px 0 rgba(139, 94, 60, 0.12), 0 4px 12px 0 rgba(139, 94, 60, 0.06)',
    card: '0 1px 2px 0 rgba(139, 94, 60, 0.04)',
    cardHover: '0 2px 6px 0 rgba(139, 94, 60, 0.08)',
    floating: '0 4px 12px 0 rgba(139, 94, 60, 0.08), 0 1px 3px 0 rgba(139, 94, 60, 0.04)',
    modal: '0 16px 48px 0 rgba(139, 94, 60, 0.12), 0 4px 12px 0 rgba(139, 94, 60, 0.06)',
    buttonHover: '0 2px 4px 0 rgba(139, 94, 60, 0.10)',
  },
  font: {
    family: {
      sans: 'Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
      mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, "Cascadia Code", Consolas, monospace',
    },
    size: {
      xs: 12,
      sm: 13,
      base: 14,
      md: 15,
      lg: 16,
      xl: 18,
      '2xl': 20,
      '3xl': 24,
      '4xl': 30,
      '5xl': 36,
    },
    // ★ Display scale (v1.39.0+) — for StatCard values and PageHeader titles.
    // Pairs with the `tracking` table below.
    display: {
      sm: { size: 24, lineHeight: 1.2, tracking: '-0.02em' },
      md: { size: 30, lineHeight: 1.15, tracking: '-0.025em' },
      lg: { size: 36, lineHeight: 1.1, tracking: '-0.03em' },
    },
    weight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700, // Avoid in production UI; see docs/DESIGN.md §4.1.
    },
    lineHeight: {
      tight: 1.15,
      snug: 1.3,
      normal: 1.5,
      relaxed: 1.625,
    },
    // ★ Letter-spacing scale (v1.39.0+) — Inter compresses as size grows.
    tracking: {
      display: '-0.025em',
      heading: '-0.02em',
      headingSm: '-0.015em',
      sub: '-0.01em',
      body: '-0.005em',
      caption: '0',
    },
    letterSpacing: {
      tight: -0.02,
      normal: 0,
      wide: 0.02,
    },
  },
  motion: {
    duration: {
      fast: 120,
      normal: 200,
      slow: 300,
    },
    easing: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
      entrance: 'cubic-bezier(0, 0, 0.2, 1)',
      exit: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
  breakpoint: {
    xs: 480,
    sm: 576,
    md: 768,
    lg: 992,
    xl: 1200,
    xxl: 1600,
  },
  z: {
    base: 0,
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modal: 1040,
    popover: 1050,
    toast: 1060,
  },
};
