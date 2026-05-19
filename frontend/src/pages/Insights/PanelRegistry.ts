import { lazy } from 'react'

export interface PanelDefinition {
  id: string
  titleKey: string        // i18n key for panel title
  descriptionKey: string  // i18n key for short description
  defaultSize: { w: number; h: number }  // grid units (12-col grid)
  minSize?: { w: number; h: number }
  component: React.LazyExoticComponent<React.ComponentType<PanelProps>>
}

export interface PanelProps {
  width?: number
  height?: number
}

// Registry — panels register themselves here
const registry = new Map<string, PanelDefinition>()

export function registerPanel(def: PanelDefinition) {
  registry.set(def.id, def)
}

export function getPanel(id: string): PanelDefinition | undefined {
  return registry.get(id)
}

export function getAllPanels(): PanelDefinition[] {
  return Array.from(registry.values())
}

// Register Phase 1 panels (lazy loaded)
registerPanel({
  id: 'delivery_calendar',
  titleKey: 'insights.delivery_calendar',
  descriptionKey: 'insights.delivery_calendar_desc',
  defaultSize: { w: 12, h: 6 },
  component: lazy(() => import('./panels/DeliveryCalendarPanel')),
})

registerPanel({
  id: 'workflow_kanban',
  titleKey: 'insights.workflow_kanban',
  descriptionKey: 'insights.workflow_kanban_desc',
  defaultSize: { w: 12, h: 6 },
  component: lazy(() => import('./panels/WorkflowKanbanPanel')),
})

registerPanel({
  id: 'budget_gauge',
  titleKey: 'insights.budget_gauge',
  descriptionKey: 'insights.budget_gauge_desc',
  defaultSize: { w: 12, h: 5 },
  component: lazy(() => import('./panels/BudgetGaugePanel')),
})

registerPanel({
  id: 'supplier_scorecard',
  titleKey: 'insights.supplier_scorecard',
  descriptionKey: 'insights.supplier_scorecard_desc',
  defaultSize: { w: 12, h: 6 },
  component: lazy(() => import('./panels/SupplierScorecardPanel')),
})

registerPanel({
  id: 'category_radar',
  titleKey: 'insights.category_radar',
  descriptionKey: 'insights.category_radar_desc',
  defaultSize: { w: 12, h: 6 },
  component: lazy(() => import('./panels/CategoryRadarPanel')),
})

registerPanel({
  id: 'approval_bottleneck',
  titleKey: 'insights.approval_bottleneck',
  descriptionKey: 'insights.approval_bottleneck_desc',
  defaultSize: { w: 12, h: 8 },
  component: lazy(() => import('./panels/ApprovalBottleneckPanel')),
})

registerPanel({
  id: 'quarterly_summary',
  titleKey: 'insights.quarterly_summary',
  descriptionKey: 'insights.quarterly_summary_desc',
  defaultSize: { w: 12, h: 5 },
  component: lazy(() => import('./panels/QuarterlySummaryPanel')),
})

registerPanel({
  id: 'anomaly_wall',
  titleKey: 'insights.anomaly_wall',
  descriptionKey: 'insights.anomaly_wall_desc',
  defaultSize: { w: 6, h: 6 },
  component: lazy(() => import('./panels/AnomalyWallPanel')),
})

registerPanel({
  id: 'cash_flow',
  titleKey: 'insights.cash_flow',
  descriptionKey: 'insights.cash_flow_desc',
  defaultSize: { w: 6, h: 6 },
  component: lazy(() => import('./panels/CashFlowForecastPanel')),
})
