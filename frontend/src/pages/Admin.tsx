import { ApartmentOutlined, AuditOutlined, BranchesOutlined, DatabaseOutlined, FileTextOutlined, ImportOutlined, RobotOutlined, SettingOutlined, TeamOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Card, Col, Row, Typography, theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { AIModelPanel } from './admin/AIModelPanel'
import { ApprovalRulesTab } from './admin/ApprovalRulesTab'
import { AuditLogsTab } from './admin/AuditLogsTab'
import { CompaniesPanel } from './admin/CompaniesPanel'
import { DepartmentsPanel } from './admin/DepartmentsPanel'
import { DocumentTemplatesPanel } from './admin/DocumentTemplatesPanel'
import { FeishuSettingsTab } from './admin/FeishuSettingsTab'
import { ImportTab } from './admin/ImportTab'
import { SystemParamsTab } from './admin/SystemParamsTab'
import { UsersPanel } from './admin/UsersPanel'

const { Title, Text } = Typography

export function AdminPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  if (user?.role !== 'admin') {
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
        case 'audit-logs': return <AuditLogsTab />
        case 'import': return <ImportTab />
        case 'document-templates': return <DocumentTemplatesPanel />
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

  const cards: { key: string; icon: JSX.Element; label: string; desc: string }[] = [
    { key: '/admin/system-params', icon: <SettingOutlined />, label: t('admin.system_params.tab_label'), desc: t('admin.system_info') },
    { key: '/admin/feishu', icon: <ThunderboltOutlined />, label: t('admin.tab.feishu'), desc: 'Feishu' },
    { key: '/admin/approval-rules', icon: <BranchesOutlined />, label: t('admin.approval_rules'), desc: 'Approval Rules' },
    { key: '/admin/users', icon: <TeamOutlined />, label: t('admin.users'), desc: 'Users' },
    { key: '/admin/companies', icon: <ApartmentOutlined />, label: t('admin.companies'), desc: 'Companies' },
    { key: '/admin/departments', icon: <DatabaseOutlined />, label: t('admin.departments'), desc: 'Departments' },
    { key: '/admin/ai-models', icon: <RobotOutlined />, label: t('admin.llm_models'), desc: 'AI Models' },
    { key: '/admin/audit-logs', icon: <AuditOutlined />, label: t('admin.tab.audit_logs'), desc: 'Audit Logs' },
    { key: '/admin/import', icon: <ImportOutlined />, label: t('admin.tab.import'), desc: 'Import' },
    { key: '/admin/document-templates', icon: <FileTextOutlined />, label: t('admin.document_templates'), desc: 'Templates' },
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
