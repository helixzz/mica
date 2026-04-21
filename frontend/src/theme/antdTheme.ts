import { ThemeConfig, theme } from 'antd';
import { tokens } from './tokens';

const baseTheme: ThemeConfig = {
  token: {
    colorPrimary: tokens.color.primary[500],
    colorSuccess: tokens.color.success[500],
    colorWarning: tokens.color.warning[500],
    colorError: tokens.color.error[500],
    colorInfo: tokens.color.info[500],
    borderRadius: tokens.radius.lg,
    fontFamily: tokens.font.family.sans,
    fontSize: tokens.font.size.base,
    lineHeight: tokens.font.lineHeight.normal,
    wireframe: false,
  },
  components: {
    Button: {
      controlHeight: 36,
      controlHeightLG: 44,
      primaryShadow: 'none',
    },
    Menu: {
      itemHeight: 40,
      itemSelectedBg: tokens.color.primary[50],
      itemSelectedColor: tokens.color.primary[700],
    },
    Table: {
      headerBg: tokens.color.neutral[50],
      rowHoverBg: tokens.color.neutral[50],
      borderColor: tokens.color.neutral[200],
    },
    Card: {
      borderRadiusLG: tokens.radius.xl,
      boxShadowTertiary: tokens.shadow.sm,
    },
    Input: {
      controlHeight: 36,
      activeBorderColor: tokens.color.primary[200],
      hoverBorderColor: tokens.color.primary[300],
    },
    Select: {
      controlHeight: 36,
    },
    DatePicker: {
      controlHeight: 36,
    },
  },
};

export const lightTheme: ThemeConfig = {
  ...baseTheme,
  algorithm: theme.defaultAlgorithm,
  token: {
    ...baseTheme.token,
    colorBgBase: tokens.color.surface.light.bg,
    colorTextBase: tokens.color.text.light.primary,
    colorBorder: tokens.color.border.light.default,
    colorBgContainer: tokens.color.surface.light.bg,
    colorBgElevated: tokens.color.surface.light.elevated,
    colorBgLayout: tokens.color.surface.light.subtle,
    colorTextSecondary: tokens.color.text.light.secondary,
    colorTextTertiary: tokens.color.text.light.tertiary,
    colorTextQuaternary: tokens.color.text.light.disabled,
  },
};

export const darkTheme: ThemeConfig = {
  ...baseTheme,
  algorithm: theme.darkAlgorithm,
  token: {
    ...baseTheme.token,
    colorBgBase: tokens.color.surface.dark.bg,
    colorTextBase: tokens.color.text.dark.primary,
    colorBorder: tokens.color.border.dark.default,
    colorBgContainer: tokens.color.surface.dark.bg,
    colorBgElevated: tokens.color.surface.dark.elevated,
    colorBgLayout: tokens.color.surface.dark.subtle,
    colorTextSecondary: tokens.color.text.dark.secondary,
    colorTextTertiary: tokens.color.text.dark.tertiary,
    colorTextQuaternary: tokens.color.text.dark.disabled,
  },
  components: {
    ...baseTheme.components,
    Menu: {
      ...baseTheme.components?.Menu,
      itemSelectedBg: tokens.color.primary[900],
      itemSelectedColor: tokens.color.primary[100],
    },
    Table: {
      ...baseTheme.components?.Table,
      headerBg: tokens.color.neutral[900],
      rowHoverBg: tokens.color.neutral[900],
      borderColor: tokens.color.neutral[800],
    },
  },
};
