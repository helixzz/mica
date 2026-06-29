import { ThemeConfig, theme } from 'antd';
import { tokens } from './tokens';

const baseTheme: ThemeConfig = {
  token: {
    colorPrimary: tokens.color.primary[500],
    colorSuccess: tokens.color.state.success[500],
    colorWarning: tokens.color.state.warning[500],
    colorError: tokens.color.state.error[500],
    colorInfo: tokens.color.state.info[500],
    borderRadius: tokens.radius.md,
    borderRadiusLG: tokens.radius.lg,
    borderRadiusSM: tokens.radius.sm,
    fontFamily: tokens.font.family.sans,
    fontFamilyCode: tokens.font.family.mono,
    fontSize: tokens.font.size.base,
    lineHeight: tokens.font.lineHeight.normal,
    wireframe: false,
    motionDurationFast: `${tokens.motion.duration.fast}ms`,
    motionDurationMid: `${tokens.motion.duration.normal}ms`,
    motionDurationSlow: `${tokens.motion.duration.slow}ms`,
    boxShadow: tokens.shadow.card,
    boxShadowSecondary: tokens.shadow.floating,
    boxShadowTertiary: tokens.shadow.card,
  },
  components: {
    Button: {
      controlHeight: 36,
      controlHeightLG: 40,
      controlHeightSM: 28,
      borderRadius: tokens.radius.md,
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      fontWeight: tokens.font.weight.medium,
    },
    Menu: {
      itemHeight: 40,
      itemSelectedBg: tokens.color.primary[50],
      itemSelectedColor: tokens.color.primary[700],
      itemHoverBg: tokens.color.neutral[50],
      itemBorderRadius: tokens.radius.md,
      activeBarBorderWidth: 0,
    },
    Table: {
      headerBg: tokens.color.neutral[50],
      headerColor: tokens.color.neutral[700],
      rowHoverBg: tokens.color.neutral[25],
      borderColor: tokens.color.border.light.hairline,
      headerSplitColor: tokens.color.border.light.hairline,
      cellPaddingBlock: 10,
      cellPaddingInline: 12,
      cellFontSize: tokens.font.size.base,
    },
    Card: {
      borderRadiusLG: tokens.radius.lg,
      paddingLG: tokens.space[5],
      colorBorderSecondary: tokens.color.border.light.hairline,
      boxShadow: 'none',
      boxShadowTertiary: tokens.shadow.card,
    },
    Input: {
      controlHeight: 36,
      borderRadius: tokens.radius.md,
      activeBorderColor: tokens.color.primary[500],
      hoverBorderColor: tokens.color.primary[300],
      activeShadow: `0 0 0 3px rgba(139, 94, 60, 0.10)`,
    },
    InputNumber: {
      controlHeight: 36,
      borderRadius: tokens.radius.md,
    },
    Select: {
      controlHeight: 36,
      borderRadius: tokens.radius.md,
      optionSelectedBg: tokens.color.primary[50],
      optionSelectedColor: tokens.color.primary[700],
      optionActiveBg: tokens.color.neutral[50],
    },
    DatePicker: {
      controlHeight: 36,
      borderRadius: tokens.radius.md,
      activeBorderColor: tokens.color.primary[500],
      hoverBorderColor: tokens.color.primary[300],
    },
    Modal: {
      borderRadiusLG: tokens.radius.lg,
      headerBg: tokens.color.surface.light.elevated,
      contentBg: tokens.color.surface.light.elevated,
      titleFontSize: tokens.font.size.xl,
      boxShadow: tokens.shadow.modal,
    },
    Drawer: {
      colorBgElevated: tokens.color.surface.light.elevated,
    },
    Tag: {
      borderRadiusSM: tokens.radius.sm,
      defaultBg: tokens.color.neutral[50],
      defaultColor: tokens.color.text.light.secondary,
    },
    Tabs: {
      itemSelectedColor: tokens.color.primary[600],
      itemHoverColor: tokens.color.primary[500],
      inkBarColor: tokens.color.primary[500],
      titleFontSize: tokens.font.size.base,
    },
    Badge: {
      borderRadiusSM: tokens.radius.sm,
    },
    Layout: {
      bodyBg: tokens.color.surface.light.bg,
      headerBg: tokens.color.surface.light.elevated,
      siderBg: tokens.color.surface.light.elevated,
      headerHeight: 56,
    },
    Form: {
      labelFontSize: tokens.font.size.lg,
      verticalLabelPadding: '0 0 4px',
      itemMarginBottom: tokens.space[4],
    },
    Tooltip: {
      borderRadius: tokens.radius.md,
      colorBgSpotlight: tokens.color.neutral[900],
    },
    Popover: {
      borderRadiusLG: tokens.radius.lg,
      boxShadowSecondary: tokens.shadow.floating,
    },
    Dropdown: {
      borderRadiusLG: tokens.radius.lg,
      controlItemBgHover: tokens.color.neutral[50],
      controlItemBgActive: tokens.color.primary[50],
      controlItemBgActiveHover: tokens.color.primary[100],
    },
    Notification: {
      borderRadiusLG: tokens.radius.lg,
    },
    Message: {
      borderRadiusLG: tokens.radius.md,
    },
    Switch: {
      colorPrimary: tokens.color.primary[500],
      colorPrimaryHover: tokens.color.primary[600],
    },
    Checkbox: {
      colorPrimary: tokens.color.primary[500],
      borderRadiusSM: tokens.radius.sm,
    },
    Radio: {
      colorPrimary: tokens.color.primary[500],
    },
    Progress: {
      defaultColor: tokens.color.primary[500],
    },
    Steps: {
      colorPrimary: tokens.color.primary[500],
    },
    Divider: {
      colorSplit: tokens.color.border.light.hairline,
    },
    Avatar: {
      borderRadius: tokens.radius.full,
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
    colorBorder: tokens.color.border.light.hairline,
    colorBorderSecondary: tokens.color.border.light.hairline,
    colorBgContainer: tokens.color.surface.light.elevated,
    colorBgElevated: tokens.color.surface.light.elevated,
    colorBgLayout: tokens.color.surface.light.bg,
    colorTextSecondary: tokens.color.text.light.secondary,
    colorTextTertiary: tokens.color.text.light.tertiary,
    colorTextQuaternary: tokens.color.text.light.disabled,
    colorTextPlaceholder: tokens.color.neutral[600],
  },
};

export const darkTheme: ThemeConfig = {
  ...baseTheme,
  algorithm: theme.darkAlgorithm,
  token: {
    ...baseTheme.token,
    colorBgBase: tokens.color.surface.dark.bg,
    colorTextBase: tokens.color.text.dark.primary,
    colorBorder: tokens.color.border.dark.hairline,
    colorBorderSecondary: tokens.color.border.dark.hairline,
    colorBgContainer: tokens.color.surface.dark.elevated,
    colorBgElevated: tokens.color.surface.dark.elevated,
    colorBgLayout: tokens.color.surface.dark.bg,
    colorTextSecondary: tokens.color.text.dark.secondary,
    colorTextTertiary: tokens.color.text.dark.tertiary,
    colorTextQuaternary: tokens.color.text.dark.disabled,
    colorTextPlaceholder: tokens.color.neutral[500],
  },
  components: {
    ...baseTheme.components,
    Menu: {
      ...baseTheme.components?.Menu,
      itemSelectedBg: tokens.color.primary[900],
      itemSelectedColor: tokens.color.primary[100],
      itemHoverBg: tokens.color.surface.dark.subtle,
    },
    Table: {
      ...baseTheme.components?.Table,
      headerBg: tokens.color.surface.dark.subtle,
      rowHoverBg: tokens.color.surface.dark.subtle,
      borderColor: tokens.color.border.dark.hairline,
      headerSplitColor: tokens.color.border.dark.hairline,
    },
    Layout: {
      ...baseTheme.components?.Layout,
      bodyBg: tokens.color.surface.dark.bg,
      headerBg: tokens.color.surface.dark.elevated,
      siderBg: tokens.color.surface.dark.elevated,
    },
    Card: {
      ...baseTheme.components?.Card,
      colorBorderSecondary: tokens.color.border.dark.hairline,
    },
    Modal: {
      ...baseTheme.components?.Modal,
      headerBg: tokens.color.surface.dark.elevated,
      contentBg: tokens.color.surface.dark.elevated,
      footerBg: tokens.color.surface.dark.elevated,
    },
    Drawer: {
      ...baseTheme.components?.Drawer,
      colorBgElevated: tokens.color.surface.dark.elevated,
    },
    Select: {
      ...baseTheme.components?.Select,
      optionSelectedBg: tokens.color.primary[900],
      optionSelectedColor: tokens.color.primary[100],
      optionActiveBg: tokens.color.surface.dark.subtle,
    },
    Dropdown: {
      ...baseTheme.components?.Dropdown,
      controlItemBgHover: tokens.color.surface.dark.subtle,
      controlItemBgActive: tokens.color.primary[900],
      controlItemBgActiveHover: tokens.color.primary[800],
    },
    Tag: {
      ...baseTheme.components?.Tag,
      defaultBg: tokens.color.surface.dark.subtle,
      defaultColor: tokens.color.text.dark.secondary,
    },
    Tooltip: {
      ...baseTheme.components?.Tooltip,
      colorBgSpotlight: tokens.color.neutral[50],
      colorTextLightSolid: tokens.color.neutral[900],
    },
    Popover: {
      ...baseTheme.components?.Popover,
      colorBgElevated: tokens.color.surface.dark.elevated,
    },
  },
};
