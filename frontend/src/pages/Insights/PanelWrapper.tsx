import { Suspense } from 'react'
import { Card, Button, Spin, theme } from 'antd'
import { CloseOutlined, ReloadOutlined, DragOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { PanelDefinition } from './PanelRegistry'
import { PanelConfig } from '../../api'

interface PanelWrapperProps {
  panelDef: PanelDefinition
  config: PanelConfig
  isEditMode: boolean
  onRemove?: (id: string) => void
}

export default function PanelWrapper({ panelDef, config, isEditMode, onRemove }: PanelWrapperProps) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: config.panel_id, disabled: !isEditMode })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    height: '100%',
    zIndex: isDragging ? 1 : 0,
    opacity: isDragging ? 0.5 : 1,
  }

  const PanelComponent = panelDef.component

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: token.paddingXS }}>
            {isEditMode && (
              <div
                {...listeners}
                style={{
                  cursor: 'grab',
                  display: 'flex',
                  alignItems: 'center',
                  color: token.colorTextTertiary,
                }}
              >
                <DragOutlined />
              </div>
            )}
            <span>{t(panelDef.titleKey)}</span>
          </div>
        }
        extra={
          <div style={{ display: 'flex', gap: token.paddingXS }}>
            {!isEditMode && (
              <Button type="text" icon={<ReloadOutlined />} size="small" />
            )}
            {isEditMode && onRemove && (
              <Button
                type="text"
                danger
                icon={<CloseOutlined />}
                size="small"
                onClick={() => onRemove(config.panel_id)}
              />
            )}
          </div>
        }
        hoverable={isEditMode}
        style={{
          height: '100%',
          border: isEditMode ? `1px dashed ${token.colorBorder}` : undefined,
          boxShadow: isDragging ? token.boxShadowSecondary : undefined,
        }}
        bodyStyle={{
          height: 'calc(100% - 56px)', // Subtract header height
          overflow: 'auto',
        }}
      >
        <Suspense
          fallback={
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Spin />
            </div>
          }
        >
          <PanelComponent width={config.w} height={config.h} />
        </Suspense>
      </Card>
    </div>
  )
}
