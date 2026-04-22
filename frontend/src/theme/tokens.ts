export const tokens = {
  color: {
    // Brand: Otter Brown (#8B5E3C as 500)
    primary: {
      50: '#F8F4F1',
      100: '#EBE1D8',
      200: '#D8C3B1',
      300: '#C4A48A',
      400: '#B18563',
      500: '#8B5E3C', // Base
      600: '#704B30',
      700: '#543824',
      800: '#382518',
      900: '#1C130C',
    },
    // Neutral: Cool gray with slight warm bias
    neutral: {
      0: '#FFFFFF',
      50: '#F7F6F5',
      100: '#EFECE9',
      200: '#DFDBD7',
      300: '#CFCAC5',
      400: '#AFA9A3',
      500: '#8F8881',
      600: '#6F6861',
      700: '#4F4943',
      800: '#2F2B27',
      900: '#1F1C19',
      950: '#0F0E0D',
    },
    // Semantic
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
    // Surface
    surface: {
      light: {
        bg: '#FFFFFF',
        subtle: '#F7F6F5',
        elevated: '#FFFFFF',
        sunken: '#EFECE9',
      },
      dark: {
        bg: '#0F0E0D',
        subtle: '#1F1C19',
        elevated: '#2F2B27',
        sunken: '#000000',
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
        subtle: '#EFECE9',
        default: '#DFDBD7',
        strong: '#AFA9A3',
      },
      dark: {
        subtle: '#3A3632',
        default: '#5A544E',
        strong: '#7A7369',
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
  radius: {
    none: 0,
    sm: 4,
    md: 6,
    lg: 8,
    xl: 12,
    full: 9999,
  },
  shadow: {
    xs: '0 1px 2px 0 rgba(15, 14, 13, 0.05)',
    sm: '0 1px 3px 0 rgba(15, 14, 13, 0.1), 0 1px 2px -1px rgba(15, 14, 13, 0.1)',
    md: '0 4px 6px -1px rgba(15, 14, 13, 0.1), 0 2px 4px -2px rgba(15, 14, 13, 0.1)',
    lg: '0 10px 15px -3px rgba(15, 14, 13, 0.1), 0 4px 6px -4px rgba(15, 14, 13, 0.1)',
    xl: '0 20px 25px -5px rgba(15, 14, 13, 0.1), 0 8px 10px -6px rgba(15, 14, 13, 0.1)',
  },
  font: {
    family: {
      sans: 'Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
      mono: '"JetBrains Mono", ui-monospace, monospace',
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
    weight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      snug: 1.375,
      normal: 1.5,
      relaxed: 1.625,
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
