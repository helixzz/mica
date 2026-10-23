import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '@/test/utils'
import { api, type ApprovalTask } from '@/api'

import { ApprovalsPage } from './Approvals'

vi.mock('@/api', () => ({
  api: {
    myPendingApprovals: vi.fn(),
    actOnApprovalTask: vi.fn(),
  },
}))

const task: ApprovalTask = {
  id: 'task-1',
  instance_id: 'instance-1',
  stage_order: 1,
  stage_name: '部门负责人',
  assignee_id: 'user-1',
  assignee_role: null,
  status: 'pending',
  action: null,
  comment: null,
  assigned_at: new Date().toISOString(),
  acted_at: null,
  biz_id: 'pr-1',
  biz_number: 'PR-2026-0095',
  biz_title: 'prod耗材补货',
  biz_amount: 29750,
  submitter_name: 'Chris Wang',
}

describe('Approvals deep link', () => {
  beforeEach(() => {
    vi.mocked(api.myPendingApprovals).mockResolvedValue([task])
    vi.mocked(api.actOnApprovalTask).mockResolvedValue(undefined)
  })

  it('opens the task named by ?task= instead of leaving it to be found', async () => {
    renderWithProviders(<ApprovalsPage />, { route: '/approvals?task=task-1' })

    await waitFor(() => {
      expect(api.myPendingApprovals).toHaveBeenCalled()
    })
    expect((await screen.findAllByText('PR-2026-0095')).length).toBeGreaterThan(0)
    expect(screen.getByText('approvals.task_detail')).toBeTruthy()
  })

  it('submits an approve decision with the typed comment', async () => {
    renderWithProviders(<ApprovalsPage />, { route: '/approvals?task=task-1' })
    await screen.findByText('approvals.task_detail')

    fireEvent.change(screen.getByPlaceholderText('approvals.comment_placeholder'), {
      target: { value: '同意采购' },
    })
    fireEvent.click(screen.getByText('button.approve'))

    await waitFor(() => {
      expect(api.actOnApprovalTask).toHaveBeenCalledWith('task-1', {
        action: 'approve',
        comment: '同意采购',
      })
    })
  })
})
