import { useState, useEffect } from 'react'
import { Row, Col, Button, Typography, Space, Empty, message, theme } from 'antd'
import { EditOutlined, SaveOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { api, PanelConfig } from '../../api'
import { getAllPanels, getPanel } from './PanelRegistry'
import PanelWrapper from './PanelWrapper'
import otterWelcome from '../../assets/illustrations/otter-welcome.svg'

const { Title } = Typography

export default function InsightsPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const [panels, setPanels] = useState<PanelConfig[]>([])
  const [isEditMode, setIsEditMode] = useState(false)
  const [loading, setLoading] = useState(true)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const data = await api.getInsightsDashboardConfig()
      if (data.panels && data.panels.length > 0) {
        setPanels(data.panels)
      } else {
        const defaults = await api.getInsightsRoleDefaults()
        setPanels(defaults.panels || [])
      }
    } catch (error) {
      console.error('Failed to load insights config:', error)
      message.error(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      await api.saveInsightsDashboardConfig(panels)
      message.success(t('insights.layout_saved'))
      setIsEditMode(false)
    } catch (error) {
      console.error('Failed to save insights config:', error)
      message.error(t('common.error'))
    }
  }

  const handleCancel = () => {
    setIsEditMode(false)
    loadConfig() // Reload to discard changes
  }

  const handleRemovePanel = (panelId: string) => {
    setPanels(panels.filter(p => p.panel_id !== panelId))
  }

  const handleAddPanel = (panelId: string) => {
    const def = getPanel(panelId)
    if (!def) return
    
    const newPanel: PanelConfig = {
      panel_id: panelId,
      x: 0,
      y: 0,
      w: def.defaultSize.w,
      h: def.defaultSize.h,
    }
    setPanels([...panels, newPanel])
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      setPanels((items) => {
        const oldIndex = items.findIndex(item => item.panel_id === active.id)
        const newIndex = items.findIndex(item => item.panel_id === over.id)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
  }

  const availablePanels = getAllPanels().filter(
    def => !panels.some(p => p.panel_id === def.id)
  )

  if (loading) {
    return null // Or a loading spinner
  }

  return (
    <div style={{ padding: token.paddingLG }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: token.marginLG }}>
        <Title level={4} style={{ margin: 0 }}>{t('insights.title')}</Title>
        <Space>
          {isEditMode ? (
            <>
              <Button icon={<CloseOutlined />} onClick={handleCancel}>
                {t('insights.cancel_edit')}
              </Button>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} style={{ backgroundColor: '#8B5E3C' }}>
                {t('insights.save_layout')}
              </Button>
            </>
          ) : (
            <Button icon={<EditOutlined />} onClick={() => setIsEditMode(true)}>
              {t('insights.edit_mode')}
            </Button>
          )}
        </Space>
      </div>

      {isEditMode && availablePanels.length > 0 && (
        <div style={{ marginBottom: token.marginLG, padding: token.padding, background: token.colorFillAlter, borderRadius: token.borderRadius }}>
          <Space wrap>
            <span style={{ color: token.colorTextSecondary }}>{t('insights.add_panel')}:</span>
            {availablePanels.map(def => (
              <Button 
                key={def.id} 
                size="small" 
                icon={<PlusOutlined />}
                onClick={() => handleAddPanel(def.id)}
              >
                {t(def.titleKey)}
              </Button>
            ))}
          </Space>
        </div>
      )}

      {panels.length === 0 ? (
        <Empty
          image={otterWelcome}
          imageStyle={{ height: 120 }}
          description={t('insights.no_panels')}
        >
          {!isEditMode && (
            <Button type="primary" onClick={() => setIsEditMode(true)} style={{ backgroundColor: '#8B5E3C' }}>
              {t('insights.edit_mode')}
            </Button>
          )}
        </Empty>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={panels.map(p => p.panel_id)}
            strategy={rectSortingStrategy}
          >
            <Row gutter={[token.marginLG, token.marginLG]}>
              {panels.map(config => {
                const def = getPanel(config.panel_id)
                if (!def) return null

                // Convert 12-col grid to AntD 24-col grid
                const span = Math.min(24, Math.max(1, config.w * 2))
                
                return (
                  <Col 
                    key={config.panel_id} 
                    xs={24} 
                    md={span > 12 ? 24 : 12} 
                    lg={span}
                    style={{ minHeight: config.h * 50 }} // Rough height estimation
                  >
                    <PanelWrapper
                      panelDef={def}
                      config={config}
                      isEditMode={isEditMode}
                      onRemove={handleRemovePanel}
                    />
                  </Col>
                )
              })}
            </Row>
          </SortableContext>
        </DndContext>
      )}
    </div>
  )
}
