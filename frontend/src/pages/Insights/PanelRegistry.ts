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
