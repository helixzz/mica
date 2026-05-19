import { ApartmentOutlined, AuditOutlined, BarChartOutlined, BranchesOutlined, ClockCircleOutlined, CloudOutlined, DatabaseOutlined, DeleteOutlined, FileTextOutlined, ImportOutlined, RobotOutlined, SettingOutlined, TeamOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Card, Col, Row, Typography, theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { AIModelPanel } from './admin/AIModelPanel'
import { AILogsPanel } from './admin/AILogsPanel'
import { ApprovalRulesTab } from './admin/ApprovalRulesTab'
import { AuditLogsTab } from './admin/AuditLogsTab'
import { CompaniesPanel } from './admin/CompaniesPanel'
import { DepartmentsPanel } from './admin/DepartmentsPanel'
import { DocumentTemplatesPanel } from './admin/DocumentTemplatesPanel'
import { FeishuSettingsTab } from './admin/FeishuSettingsTab'
import { ImportTab } from './admin/ImportTab'
import { RoutingsPanel } from './admin/RoutingsPanel'
import { SchedulerTab } from './admin/SchedulerTab'
import { SystemParamsTab } from './admin/SystemParamsTab'
import { UsersPanel } from './admin/UsersPanel'

const { Title, Text } = Typography

const isAdmin = (u: any) => u?.role === 'admin'

export function AdminPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  if (!isAdmin(user)) {
    return <Card><Title level={4}>{t('error.permission_denied')}</Title><Text type="secondary">{t('admin.admin_only')}</Text></Card>
  }

  const section = location.pathname !== '/admin' ? location.pathname.replace('/admin/', '') : ''

  if (section) {
    const render = () => {
      switch (section) {
        case 'system-params': return <SystemParamsTab />
        case 'feishu': return <FeishuSettingsTab />
        case 'approval-rules': return <ApprovalRulesTab />
        case 'users': return <UsersPanel />
        case 'companies': return <CompaniesPanel />
        case 'departments': return <DepartmentsPanel />
        case 'ai-models': return <AIModelPanel />
        case 'ai-logs': return <AILogsPanel />
        case 'ai-routing': return <RoutingsPanel />
        case 'audit-logs': return <AuditLogsTab />
        case 'import': return <ImportTab />
        case 'document-templates': return <DocumentTemplatesPanel />
        case 'scheduler': return <SchedulerTab />
        default: return null
      }
    }
    return (
      <div style={{ padding: token.paddingLG }}>
        <Text type="secondary" style={{ cursor: 'pointer' }} onClick={() => navigate('/admin')}>← {t('admin.back_to_overview')}</Text>
        <div style={{ marginTop: 16 }}>{render()}</div>
      </div>
    )
  }

  const cards = [
    { key: '/admin/system-params', icon: <SettingOutlined />, label: t('admin.system_params.tab_label'), desc: t('admin.system_params_desc') },
    { key: '/admin/feishu', icon: <ThunderboltOutlined />, label: t('admin.tab.feishu'), desc: t('admin.feishu_desc') },
    { key: '/admin/approval-rules', icon: <BranchesOutlined />, label: t('admin.approval_rules'), desc: t('admin.approval_rules_desc') },
    { key: '/admin/users', icon: <TeamOutlined />, label: t('admin.users'), desc: t('admin.users_desc') },
    { key: '/admin/companies', icon: <ApartmentOutlined />, label: t('admin.companies'), desc: t('admin.companies_desc') },
    { key: '/admin/departments', icon: <DatabaseOutlined />, label: t('admin.departments'), desc: t('admin.departments_desc') },
    { key: '/admin/ai-models', icon: <RobotOutlined />, label: t('admin.llm_models'), desc: t('admin.llm_models_desc') },
    { key: '/admin/ai-routing', icon: <BranchesOutlined />, label: t('admin.ai_routing'), desc: t('admin.ai_routing_desc') },
    { key: '/admin/ai-logs', icon: <BarChartOutlined />, label: t('admin.ai_logs'), desc: t('admin.ai_logs_desc') },
    { key: '/admin/audit-logs', icon: <AuditOutlined />, label: t('admin.tab.audit_logs'), desc: t('admin.audit_logs_desc') },
    { key: '/admin/import', icon: <ImportOutlined />, label: t('admin.tab.import'), desc: t('admin.import_desc') },
    { key: '/admin/document-templates', icon: <FileTextOutlined />, label: t('admin.document_templates'), desc: t('admin.document_templates_desc') },
    { key: '/admin/scheduler', icon: <ClockCircleOutlined />, label: t('admin.scheduler_tab'), desc: t('admin.scheduler_help') },
  ]

  return (
    <div style={{ padding: token.paddingLG }}>
      <Title level={3} style={{ marginBottom: token.marginLG }}>{t('admin.admin_console')}</Title>
      <Row gutter={[16, 16]}>
        {cards.map(c => (
          <Col xs={24} sm={12} md={8} lg={6} key={c.key}>
            <Card hoverable onClick={() => navigate(c.key)} style={{ height: '100%', cursor: 'pointer' }}>
              <div style={{ fontSize: 32, color: token.colorPrimary, marginBottom: 12 }}>{c.icon}</div>
              <Title level={5} style={{ margin: '4px 0' }}>{c.label}</Title>
              <Text type="secondary" style={{ fontSize: 13 }}>{c.desc}</Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
