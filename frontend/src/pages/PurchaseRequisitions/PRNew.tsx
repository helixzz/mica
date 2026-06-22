import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type ApprovalPreviewCandidate, type ClassificationItem, type Department, flattenCategoryTree, type Item, type PRItem, type Supplier, type ProxyCandidate } from '@/api'
import { client, extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { AIStreamButton } from '@/components/AIStreamButton'
import { ItemPickerWithCreate } from '@/components/ItemPickerWithCreate'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import ApprovalPreview from '@/components/PR/ApprovalPreview'
import { PRQuoteConfirmModal } from '@/components/PRQuoteConfirmModal'
import { MarqueeOption } from '@/components/ui/MarqueeOption'
import { useAutosave } from '@/hooks/useAutosave'
import { fmtAmount } from '@/utils/format'

interface LineForm {
  key: number
  line_no: number
  item_id: string | null
  item_name: string
  specification: string | null
  supplier_id: string | null
  qty: number
  uom: string
  unit_price: number
}

export function PRNewPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [companies, setCompanies] = useState<{ id: string; name_zh: string }[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [costCenters, setCostCenters] = useState<{ id: string; label_zh: string }[]>([])
  const [expenseTypes, setExpenseTypes] = useState<{ id: string; label_zh: string }[]>([])
  const [procCategories, setProcCategories] = useState<ClassificationItem[]>([])
  const [aiFeatures, setAiFeatures] = useState<Record<string, boolean>>({})
  const [firstStageCandidates, setFirstStageCandidates] = useState<ApprovalPreviewCandidate[]>([])
  const [lines, setLines] = useState<LineForm[]>([
    { key: 1, line_no: 1, item_id: null, item_name: '', specification: '', supplier_id: null, qty: 1, uom: 'EA', unit_price: 0 },
  ])
  const [submitting, setSubmitting] = useState(false)
  const [savedPRId, setSavedPRId] = useState<string | null>(null)
  const { user } = useAuth()
  const isRequester = user?.role === 'requester'
  const canProxy = ['admin', 'procurement_mgr', 'it_buyer'].includes(user?.role ?? '')
  const [proxyCandidates, setProxyCandidates] = useState<ProxyCandidate[]>([])
  const autosave = useAutosave(`pr-new-${user?.id || 'anon'}`)
  const [autosaveDismissed, setAutosaveDismissed] = useState(false)
  const [refPrices, setRefPrices] = useState<Record<string, { latest_price: number | null; avg_price: number | null }>>({})
  const copyId = useParams<{ copyId: string }>().copyId

  useEffect(() => {
    void api.suppliers().then(setSuppliers)
    void api.items().then(setItems)
    void api.companies().then(setCompanies)
    void api.departments().then(setDepartments).catch(() => {})
    void api.listCostCenters().then(setCostCenters)
    void api.listLookupValues('expense_type').then(setExpenseTypes)
    void api.getCategoryTree().then((tree) => setProcCategories(flattenCategoryTree(tree)))
    void client.get<Record<string, boolean>>('/ai/features-available').then((r) => setAiFeatures(r.data)).catch(() => {})
    if (canProxy) {
      void api.listProxyCandidates().then(setProxyCandidates).catch(() => {})
    }
  }, [canProxy])

  useEffect(() => {
    if (!canProxy) return
    void api.listProxyCandidates().then(setProxyCandidates).catch(() => {})
  }, [canProxy])

  useEffect(() => {
    if (!copyId) return
    void (async () => {
      try {
        const pr = await api.getPR(copyId)
        form.setFieldsValue({
          title: pr.title,
          business_reason: pr.business_reason || '',
          currency: pr.currency,
          required_date: pr.required_date ? dayjs(pr.required_date) : undefined,
          company_id: pr.company_id || undefined,
          department_id: pr.department_id || undefined,
          cost_center_id: pr.cost_center_id || undefined,
          expense_type_id: pr.expense_type_id || undefined,
          procurement_category_id: pr.procurement_category_id || undefined,
          preferred_first_approver_id: pr.preferred_first_approver_id || undefined,
        })
        setLines(
          (pr.items || []).map((item, i) => ({
            key: Date.now() + i,
            line_no: i + 1,
            item_id: item.item_id,
            item_name: item.item_name,
            specification: item.specification,
            supplier_id: item.supplier_id,
            qty: Number(item.qty),
            uom: item.uom,
            unit_price: Number(item.unit_price),
          })),
        )
        void message.info(t('pr.copying_from', { title: pr.title }))
        navigate('/purchase-requisitions/new', { replace: true })
      } catch {
        void message.error(t('error.unexpected'))
        navigate('/purchase-requisitions/new', { replace: true })
      }
    })()
  }, [copyId])

  useEffect(() => {
    const formValues = form.getFieldsValue()
    autosave.save({ ...formValues, items: lines })
  })

  const addLine = () => {
    setLines((ls) => [
      ...ls,
      {
        key: Date.now(),
        line_no: ls.length + 1,
        item_id: null,
        item_name: '',
        specification: '',
        supplier_id: null,
        qty: 1,
        uom: 'EA',
        unit_price: 0,
      },
    ])
  }

  const updateLine = <K extends keyof LineForm>(key: number, field: K, value: LineForm[K]) => {
    setLines((ls) =>
      ls.map((l) => {
        if (l.key !== key) return l
        const updated = { ...l, [field]: value }
        if (field === 'item_id' && value) {
          const item = items.find((i) => i.id === value)
          if (item) {
            updated.item_name = item.name
            updated.specification = item.specification || ''
          }
          void client
            .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(
              `/sku/reference-prices?item_ids=${value}`,
            )
            .then((r) => {
              const price = r.data[String(value)]?.latest_price
              if (price != null) {
                setLines((ls) => ls.map((l) => (l.key === key ? { ...l, unit_price: price } : l)))
              }
              setRefPrices((prev) => ({ ...prev, ...r.data }))
            })
            .catch(() => {})
        }
        return updated
      }),
    )
  }

  const onItemSelect = (key: number, itemId: string | null, picked?: Item | null) => {
    if (!itemId) {
      updateLine(key, 'item_id', null)
      return
    }
    const it = picked ?? items.find((i) => i.id === itemId)
    if (!it) return
    setLines((ls) =>
      ls.map((l) =>
        l.key === key
          ? { ...l, item_id: it.id, item_name: it.name, specification: it.specification, uom: it.uom }
          : l
      )
    )
    void client
      .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(
        `/sku/reference-prices?item_ids=${itemId}`,
      )
      .then((r) => {
        const price = r.data[itemId]?.latest_price
        if (price != null) {
          setLines((ls) => ls.map((l) => (l.key === key ? { ...l, unit_price: price } : l)))
        }
        setRefPrices((prev) => ({ ...prev, ...r.data }))
      })
      .catch(() => {})
  }

  const removeLine = (key: number) => {
    setLines((ls) => ls.filter((l) => l.key !== key).map((l, i) => ({ ...l, line_no: i + 1 })))
  }

  const total = lines.reduce((s, l) => s + l.qty * l.unit_price, 0)
  const watchedCurrency = Form.useWatch('currency', form) || 'CNY'
  const watchedRequesterId = Form.useWatch('requester_id', form)
  const watchedDepartmentId = Form.useWatch('department_id', form)
  const watchedCostCenterId = Form.useWatch('cost_center_id', form)
  const watchedPreferredApproverId = Form.useWatch('preferred_first_approver_id', form)
  const isProxying = canProxy && watchedRequesterId && watchedRequesterId !== user?.id

  const filteredDepartments = (() => {
    const companyId = form.getFieldValue('company_id') as string | undefined
    if (!companyId) return departments
    return departments.filter((d) => d.company_id === companyId)
  })()

  const onFinish = async (saveOnly: boolean) => {
    try {
      const values = await form.validateFields()
      const validLines = lines.filter((l) => l.item_name.trim())
      setSubmitting(true)
      const payload = {
        title: values.title,
        business_reason: values.business_reason,
        currency: values.currency || 'CNY',
        required_date: values.required_date ? values.required_date.format('YYYY-MM-DD') : null,
        requester_id: canProxy ? (values.requester_id || null) : null,
        company_id: values.company_id || null,
        department_id: values.department_id || null,
        cost_center_id: values.cost_center_id || null,
        expense_type_id: values.expense_type_id || null,
        procurement_category_id: values.procurement_category_id || null,
        preferred_first_approver_id: values.preferred_first_approver_id || null,
        items: validLines.map<PRItem>((l) => ({
          line_no: l.line_no,
          item_id: l.item_id,
          item_name: l.item_name,
          specification: l.specification,
          supplier_id: l.supplier_id,
          qty: l.qty,
          uom: l.uom,
          unit_price: l.unit_price,
        })),
      }
      const pr = await api.createPR(payload)
      autosave.clear()
      if (!saveOnly) {
        await api.submitPR(pr.id)
        void message.success(t('message.submit_success'))
        navigate(`/purchase-requisitions/${pr.id}`)
      } else {
        void message.success(t('message.save_success'))
        setSavedPRId(pr.id)
      }
    } catch (e) {
      const err = extractError(e)
      void message.error(err.detail || t('error.unexpected'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        {t('button.create')} · {t('nav.purchase_requisitions')}
      </Typography.Title>

      {isRequester && (
        <Alert
          type="info"
          showIcon
          message={t('pr.guide_title')}
          description={
            <ul style={{ margin: '4px 0 0', paddingLeft: 20, fontSize: 13 }}>
              <li>{t('pr.guide_title_field')}</li>
              <li>{t('pr.guide_required_fields')}</li>
              <li>{t('pr.guide_items')}</li>
              <li>{t('pr.guide_price')}</li>
              <li>{t('pr.guide_reason')}</li>
            </ul>
          }
        />
      )}

      {!autosaveDismissed && autosave.hasAutosave && autosave.savedAt && (
        <AutosaveBanner
          savedAt={autosave.savedAt}
          onRestore={() => {
            const vals = autosave.restore()
            if (vals) {
              const items = vals.items as LineForm[] | undefined
              if (items) {
                setLines(items)
                form.setFieldsValue({ ...vals, items: undefined })
              } else {
                form.setFieldsValue(vals as Record<string, unknown>)
              }
            }
          }}
          onDismiss={() => setAutosaveDismissed(true)}
        />
      )}
      {!autosave.storageAvailable && <AutosaveUnavailableBanner />}

      {isProxying && (
        <Alert
          type="info"
          showIcon
          message={t('pr.proxy_mode_active')}
          description={t('pr.proxy_mode_help', { name: proxyCandidates.find((c) => c.id === watchedRequesterId)?.display_name ?? '' })}
        />
      )}

      <Card>
        <Form form={form} layout="vertical" initialValues={{ currency: 'CNY', requester_id: canProxy ? user?.id : undefined }}>
          {canProxy && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label={t('pr.requester_label')}
                  name="requester_id"
                  help={t('pr.requester_help')}
                  rules={[{ required: true, message: t('validation.select_requester') }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder={t('pr.select_requester')}
                    popupMatchSelectWidth={false}
                    optionRender={(option) => <MarqueeOption>{option.label}</MarqueeOption>}
                    options={proxyCandidates.map((u) => ({
                      value: u.id,
                      label: `${u.display_name} (${u.email})`,
                    }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          )}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t('field.title')}
                name="title"
                help={t('pr.title_help')}
                rules={[{ required: true }]}
              >
                <Input placeholder={t('placeholder.enter_title')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.currency')} name="currency">
                <Select options={[{ value: 'CNY', label: 'CNY ¥' }, { value: 'USD', label: 'USD $' }, { value: 'EUR', label: 'EUR €' }, { value: 'GBP', label: 'GBP £' }, { value: 'JPY', label: 'JPY ¥' }, { value: 'KRW', label: 'KRW ₩' }, { value: 'HKD', label: 'HKD HK$' }, { value: 'TWD', label: 'TWD NT$' }]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.required_date')} name="required_date">
                
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label={t('pr.company_label')} name="company_id" help={t('pr.company_help')} rules={[{ required: true, message: t('validation.select_company') }]}>
                <Select
                  placeholder={t('pr.select_company')}
                  options={companies.map((c) => ({ value: c.id, label: c.name_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.cost_center_label')} name="cost_center_id" help={t('pr.cost_center_help')} rules={[{ required: true, message: t('validation.select_cost_center') }]}>
                <Select
                  placeholder={t('pr.select_cost_center')}
                  options={costCenters.map((c) => ({ value: c.id, label: c.label_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.expense_type_label')} name="expense_type_id" help={t('pr.expense_type_help')} rules={[{ required: true, message: t('validation.select_expense_type') }]}>
                <Select
                  placeholder="CapEx / OpEx"
                  options={expenseTypes.map((e) => ({ value: e.id, label: e.label_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.category_label')} name="procurement_category_id" help={t('pr.category_help')}>
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('pr.select_category')}
                  options={procCategories.map((c) => ({
                    value: c.id,
                    label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t('pr.acting_department_label')}
                name="department_id"
                help={t('pr.acting_department_help')}
              >
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('pr.select_acting_department')}
                  popupMatchSelectWidth={false}
                  optionRender={(option) => <MarqueeOption>{option.label}</MarqueeOption>}
                  options={filteredDepartments.map((d) => ({
                    value: d.id,
                    label: `${d.name_zh}${d.code ? ` (${d.code})` : ''}`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t('pr.preferred_approver_label')}
                name="preferred_first_approver_id"
                help={t('pr.preferred_approver_help')}
              >
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('pr.preferred_approver_auto')}
                  popupMatchSelectWidth={false}
                  optionRender={(option) => <MarqueeOption>{option.label}</MarqueeOption>}
                  options={firstStageCandidates.map((c) => ({
                    value: c.user_id,
                    label: c.via_delegation_from
                      ? `${c.display_name} · ${t('approval_preview.via_delegation')}`
                      : c.display_name,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.business_reason')} name="business_reason" help={t('pr.business_reason_help')}>
            <Input.TextArea rows={3} placeholder={t('placeholder.enter_reason')} />
          </Form.Item>
          <Space>
            <AIStreamButton
              feature="pr_description_polish"
              body={{ draft: Form.useWatch('business_reason', form) || '' }}
              onChunk={(chunk) => {
                const current = form.getFieldValue('business_reason') || ''
                form.setFieldValue('business_reason', current + chunk)
              }}
              disabled={!Form.useWatch('business_reason', form)}
              available={aiFeatures['pr_description_polish'] === true}
              label={t('button.ai_polish')}
            />
          </Space>
        </Form>
      </Card>

      {total > 0 && (
        <Card title={t('approval_preview.title')} size="small">
          <ApprovalPreview
            amount={total}
            requesterId={canProxy ? watchedRequesterId : null}
            departmentId={watchedDepartmentId}
            costCenterId={watchedCostCenterId}
            onCandidatesLoaded={setFirstStageCandidates}
          />
          {watchedPreferredApproverId &&
            !firstStageCandidates.some((c) => c.user_id === watchedPreferredApproverId) && (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 8 }}
                message={t('approval_preview.preferred_no_longer_valid')}
              />
            )}
        </Card>
      )}

      <Card
        title={t('nav.purchase_requisitions')}
        extra={
          <Button icon={<PlusOutlined />} onClick={addLine}>
            {t('button.add_line')}
          </Button>
        }
      >
        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          {t('pr.line_items_help')}
        </Typography.Text>
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {lines.map((line, idx) => (
            <Card key={line.key} size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Typography.Text strong>#{idx + 1}</Typography.Text>
                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeLine(line.key)} />
              </div>
              <Row gutter={[12, 12]}>
                <Col xs={24} md={isRequester ? 24 : 14}>
                  <div style={{ marginBottom: 4 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.item_name')}</Typography.Text>
                  </div>
                  <ItemPickerWithCreate
                    placeholder={isRequester ? t('pr.select_item_requester') : t('placeholder.select_item')}
                    value={line.item_id ?? undefined}
                    onChange={(v, picked) => onItemSelect(line.key, v, picked)}
                  />
                  {line.item_id && refPrices[line.item_id] && (
                    <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 2 }}>
                      {t('sku.ref_latest')}: {fmtAmount(refPrices[line.item_id].latest_price, 'CNY')}
                      {refPrices[line.item_id].avg_price ? ` · ${t('sku.ref_avg')}: ${fmtAmount(refPrices[line.item_id].avg_price, 'CNY')}` : ''}
                    </Typography.Text>
                  )}
                </Col>
                {!isRequester && (
                  <Col xs={24} md={10}>
                    <div style={{ marginBottom: 4 }}>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.supplier')}</Typography.Text>
                    </div>
                    <Select
                      style={{ width: '100%' }}
                      placeholder={t('placeholder.select_supplier')}
                      value={line.supplier_id ?? undefined}
                      onChange={(v: string) => updateLine(line.key, 'supplier_id', v)}
                      options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                      showSearch
                      optionFilterProp="label"
                      allowClear
                      popupMatchSelectWidth={false}
                    />
                  </Col>
                )}
                <Col xs={6} md={4}>
                  <div style={{ marginBottom: 4 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.qty')}</Typography.Text>
                  </div>
                  <InputNumber min={0.0001} value={line.qty} onChange={(v) => updateLine(line.key, 'qty', Number(v ?? 0))} style={{ width: '100%' }} />
                </Col>
                <Col xs={4} md={3}>
                  <div style={{ marginBottom: 4 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.uom')}</Typography.Text>
                  </div>
                  <Input value={line.uom} onChange={(e) => updateLine(line.key, 'uom', e.target.value)} />
                </Col>
                <Col xs={8} md={5}>
                  <div style={{ marginBottom: 4 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.unit_price')}</Typography.Text>
                  </div>
                  <InputNumber min={0} value={line.unit_price || undefined} onChange={(v) => updateLine(line.key, 'unit_price', Number(v ?? 0))} style={{ width: '100%' }} placeholder={isRequester ? t('pr.price_placeholder') : undefined} />
                </Col>
                <Col xs={6} md={4}>
                  <div style={{ marginBottom: 4 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.amount')}</Typography.Text>
                  </div>
                  <div style={{ lineHeight: '32px', fontWeight: 600, textAlign: 'right' }}>
                    {line.qty * (line.unit_price || 0) > 0 ? fmtAmount(line.qty * (line.unit_price || 0), watchedCurrency) : '-'}
                  </div>
                </Col>
              </Row>
            </Card>
          ))}
        </Space>
        <div style={{ textAlign: 'right', padding: '12px 0 0' }}>
          <Typography.Text strong style={{ fontSize: 16 }}>
            {t('field.total_amount')}: {total > 0 ? fmtAmount(total, watchedCurrency) : '-'}
          </Typography.Text>
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate(-1)}>{t('button.cancel')}</Button>
        <Button loading={submitting} onClick={() => onFinish(true)}>
          {t('button.save')}
        </Button>
        <Button type="primary" loading={submitting} onClick={() => onFinish(false)}>
          {t('button.submit_for_approval')}
        </Button>
      </Space>

      {savedPRId && (
        <PRQuoteConfirmModal
          prId={savedPRId}
          open={!!savedPRId}
          onClose={() => {
            const id = savedPRId
            setSavedPRId(null)
            navigate(`/purchase-requisitions/${id}`)
          }}
        />
      )}
    </Space>
  )
}
