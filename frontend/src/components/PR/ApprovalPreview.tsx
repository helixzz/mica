import { Alert, Skeleton, Steps, Tag, Tooltip, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ApprovalPreview, type ApprovalPreviewCandidate } from '@/api'
import { extractError } from '@/api/client'

const { Text } = Typography

interface ApprovalPreviewProps {
  amount: number | string
  requesterId?: string | null
  departmentId?: string | null
  costCenterId?: string | null
  bizType?: string
  onCandidatesLoaded?: (firstStageCandidates: ApprovalPreviewCandidate[]) => void
}

function CandidateTag({ candidate }: { candidate: ApprovalPreviewCandidate }) {
  const { t } = useTranslation()
  if (candidate.via_delegation_from) {
    return (
      <Tooltip title={t('approval_preview.via_delegation')}>
        <Tag color="purple">{candidate.display_name}</Tag>
      </Tooltip>
    )
  }
  return <Tag color="blue">{candidate.display_name}</Tag>
}

export default function ApprovalPreview({
  amount,
  requesterId,
  departmentId,
  costCenterId,
  bizType = 'purchase_requisition',
  onCandidatesLoaded,
}: ApprovalPreviewProps) {
  const { t } = useTranslation()
  const [preview, setPreview] = useState<ApprovalPreview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const numericAmount = typeof amount === 'string' ? Number(amount) : amount
    if (!Number.isFinite(numericAmount) || numericAmount < 0) {
      setPreview(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .previewApproval({
        biz_type: bizType,
        amount: numericAmount,
        requester_id: requesterId ?? null,
        department_id: departmentId ?? null,
        cost_center_id: costCenterId ?? null,
      })
      .then((data) => {
        if (cancelled) return
        setPreview(data)
        if (onCandidatesLoaded && data.stages.length > 0) {
          onCandidatesLoaded(data.stages[0].candidates)
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(extractError(e).detail)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [amount, requesterId, departmentId, costCenterId, bizType, onCandidatesLoaded])

  if (loading && !preview) {
    return <Skeleton active paragraph={{ rows: 2 }} />
  }
  if (error) {
    return <Alert type="warning" showIcon message={error} />
  }
  if (!preview) {
    return null
  }
  if (preview.stages.length === 0) {
    return <Alert type="info" showIcon message={t('approval_preview.no_stages')} />
  }

  const items = preview.stages.map((stage) => ({
    title: stage.stage_name,
    description: (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
        {stage.candidates.length === 0 ? (
          <Text type="warning">{t('approval_preview.no_candidates')}</Text>
        ) : (
          stage.candidates.map((c) => <CandidateTag key={c.user_id} candidate={c} />)
        )}
        {stage.fallback_to_admin && (
          <Tooltip title={t('approval_preview.fallback_admin_tip')}>
            <Tag color="orange">{t('approval_preview.fallback_admin')}</Tag>
          </Tooltip>
        )}
      </div>
    ),
  }))

  return (
    <div style={{ marginTop: 8 }}>
      {preview.is_legacy_fallback ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 8 }}
          message={t('approval_preview.legacy_fallback')}
        />
      ) : preview.matched_rule_name ? (
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          {t('approval_preview.matched_rule')}: {preview.matched_rule_name}
        </Text>
      ) : null}
      <Steps direction="vertical" size="small" current={-1} items={items} />
    </div>
  )
}
