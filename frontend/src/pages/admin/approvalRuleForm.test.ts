import { describe, expect, it } from 'vitest'

import {
  createDefaultApprovalRuleForm,
  mapApprovalRuleFormToPayload,
  mapApprovalRuleToForm,
} from './approvalRuleForm'

describe('approvalRuleForm helpers', () => {
  it('creates a default structured rule form', () => {
    expect(createDefaultApprovalRuleForm('部门审批')).toEqual({
      priority: 100,
      is_active: true,
      stages: [{ stage_name: '部门审批', approver_role: 'dept_manager' }],
    })
  })

  it('hydrates edit form state from api rule and sorts stages by order', () => {
    expect(
      mapApprovalRuleToForm(
        {
          id: 'rule-1',
          name: '原规则',
          biz_type: 'purchase_requisition',
          amount_min: 0,
          amount_max: 100000,
          priority: 50,
          is_active: true,
          stages: [
            { stage_name: '采购经理审批', approver_role: 'procurement_mgr', order: 2 },
            { stage_name: '部门审批', approver_role: 'dept_manager', order: 1 },
          ],
        },
        '默认阶段',
      ),
    ).toEqual({
      name: '原规则',
      biz_type: 'purchase_requisition',
      amount_min: 0,
      amount_max: 100000,
      priority: 50,
      is_active: true,
      stages: [
        { stage_name: '部门审批', approver_role: 'dept_manager' },
        { stage_name: '采购经理审批', approver_role: 'procurement_mgr' },
      ],
    })
  })

  it('serializes structured stage form values into ordered api payload', () => {
    expect(
      mapApprovalRuleFormToPayload({
        name: '测试审批规则',
        biz_type: 'purchase_requisition',
        amount_min: 0,
        amount_max: 100000,
        priority: 100,
        is_active: true,
        stages: [
          { stage_name: '一级审批', approver_role: 'dept_manager' },
          { stage_name: '二级审批', approver_role: 'procurement_mgr' },
        ],
      }),
    ).toEqual({
      name: '测试审批规则',
      biz_type: 'purchase_requisition',
      amount_min: 0,
      amount_max: 100000,
      priority: 100,
      is_active: true,
      stages: [
        { stage_name: '一级审批', approver_role: 'dept_manager', order: 1 },
        { stage_name: '二级审批', approver_role: 'procurement_mgr', order: 2 },
      ],
    })
  })
})
