import { ReloadOutlined } from '@ant-design/icons'
import { Button, DatePicker, Form, Input, InputNumber, Modal, Space, message } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Contract } from '@/api'
import { extractError } from '@/api/client'

type Mode = 'create' | 'edit'

export interface ContractFormValues {
  contract_number?: string | null
  title: string
  total_amount: number
  signed_date?: Dayjs | null
  effective_date?: Dayjs | null
  expiry_date?: Dayjs | null
  notes?: string | null
  change_reason?: string | null
}

interface ContractFormModalProps {
  open: boolean
  mode: Mode
  contract?: Contract | null
  poId?: string
  onClose: () => void
  onSaved: (contract: Contract) => void
}

export function ContractFormModal({
  open,
  mode,
  contract,
  poId,
  onClose,
  onSaved,
}: ContractFormModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm<ContractFormValues>()
  const [suggesting, setSuggesting] = useState(false)

  const fetchSuggestion = async () => {
    setSuggesting(true)
    try {
      const { suggested_number } = await api.suggestContractNumber()
      form.setFieldsValue({ contract_number: suggested_number })
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setSuggesting(false)
    }
  }

  useEffect(() => {
    if (!open) return
    if (mode === 'edit' && contract) {
      form.setFieldsValue({
        contract_number: contract.contract_number,
        title: contract.title,
        total_amount: Number(contract.total_amount),
        signed_date: contract.signed_date ? dayjs(contract.signed_date) : null,
        effective_date: contract.effective_date ? dayjs(contract.effective_date) : null,
        expiry_date: contract.expiry_date ? dayjs(contract.expiry_date) : null,
        notes: contract.notes,
        change_reason: null,
      })
    } else {
      form.resetFields()
      void fetchSuggestion()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, mode, contract, form])

  const handleOk = async () => {
    const values = await form.validateFields()
    const basePayload = {
      title: values.title,
      total_amount: values.total_amount,
      signed_date: values.signed_date ? values.signed_date.format('YYYY-MM-DD') : null,
      effective_date: values.effective_date ? values.effective_date.format('YYYY-MM-DD') : null,
      expiry_date: values.expiry_date ? values.expiry_date.format('YYYY-MM-DD') : null,
      notes: values.notes ?? null,
    }
    try {
      let saved: Contract
      if (mode === 'create') {
        if (!poId) throw new Error('poId is required for create')
        saved = await api.createContract({
          po_id: poId,
          ...basePayload,
          contract_number: values.contract_number?.trim() || null,
        })
      } else {
        if (!contract) throw new Error('contract is required for edit')
        saved = await api.updateContract(contract.id, {
          ...basePayload,
          change_reason: values.change_reason ?? null,
        })
      }
      void message.success(
        mode === 'create' ? t('contract.created_ok') : t('contract.updated_ok'),
      )
      onSaved(saved)
      onClose()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  return (
    <Modal
      title={mode === 'create' ? t('contract.create_title') : t('contract.edit_title')}
      open={open}
      onOk={handleOk}
      onCancel={onClose}
      okText={t('button.save')}
      cancelText={t('button.cancel')}
      width={640}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" preserve={false}>
        {mode === 'create' && (
          <Form.Item
            name="contract_number"
            label={t('contract.contract_number_field')}
            help={t('contract.contract_number_help')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input
              addonAfter={
                <Space size={4}>
                  <Button
                    type="link"
                    size="small"
                    icon={<ReloadOutlined spin={suggesting} />}
                    onClick={fetchSuggestion}
                    style={{ padding: 0, height: 22 }}
                  >
                    {t('contract.contract_number_regenerate')}
                  </Button>
                </Space>
              }
            />
          </Form.Item>
        )}
        <Form.Item
          name="title"
          label={t('field.title')}
          rules={[{ required: true, message: t('validation.required') }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="total_amount"
          label={t('field.total_amount')}
          rules={[{ required: true, message: t('validation.required') }]}
        >
          <InputNumber style={{ width: '100%' }} min={0} precision={2} prefix="¥" />
        </Form.Item>
        <Form.Item name="signed_date" label={t('field.signed_date')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="effective_date" label={t('field.effective_date')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="expiry_date" label={t('field.expiry_date')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="notes" label={t('field.notes')}>
          <Input.TextArea rows={2} />
        </Form.Item>
        {mode === 'edit' && (
          <Form.Item name="change_reason" label={t('contract.change_reason')}>
            <Input.TextArea rows={2} placeholder={t('contract.change_reason_placeholder')} />
          </Form.Item>
        )}
      </Form>
    </Modal>
  )
}
