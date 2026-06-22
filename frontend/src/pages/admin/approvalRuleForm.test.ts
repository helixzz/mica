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
      department_ids: null,
      cost_center_ids: null,
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
      department_ids: null,
      cost_center_ids: null,
      priority: 50,
      is_active: true,
      stages: [
        { stage_name: '部门审批', approver_role: 'dept_manager' },
        { stage_name: '采购经理审批', approver_role: 'procurement_mgr' },
      ],
    })
  })

  it('hydrates dept_ids/cost_center_ids when api rule has filters set', () => {
    const result = mapApprovalRuleToForm(
      {
        id: 'rule-2',
        name: 'IT 部门规则',
        biz_type: 'purchase_requisition',
        amount_min: null,
        amount_max: null,
        department_ids: ['dept-it'],
        cost_center_ids: ['cc-1', 'cc-2'],
        priority: 10,
        is_active: true,
        stages: [{ stage_name: '部门审批', approver_role: 'dept_manager', order: 1 }],
      },
      '默认阶段',
    )
    expect(result.department_ids).toEqual(['dept-it'])
    expect(result.cost_center_ids).toEqual(['cc-1', 'cc-2'])
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
      department_ids: null,
      cost_center_ids: null,
      priority: 100,
      is_active: true,
      stages: [
        { stage_name: '一级审批', approver_role: 'dept_manager', order: 1 },
        { stage_name: '二级审批', approver_role: 'procurement_mgr', order: 2 },
      ],
    })
  })

  it('serializes empty arrays as null in payload (semantic = no filter)', () => {
    const payload = mapApprovalRuleFormToPayload({
      name: 'x',
      biz_type: 'purchase_requisition',
      department_ids: [],
      cost_center_ids: [],
      priority: 100,
      is_active: true,
      stages: [{ stage_name: 'a', approver_role: 'dept_manager' }],
    })
    expect(payload.department_ids).toBeNull()
    expect(payload.cost_center_ids).toBeNull()
  })

  it('preserves non-empty arrays in payload', () => {
    const payload = mapApprovalRuleFormToPayload({
      name: 'x',
      biz_type: 'purchase_requisition',
      department_ids: ['d1', 'd2'],
      cost_center_ids: ['cc1'],
      priority: 100,
      is_active: true,
      stages: [{ stage_name: 'a', approver_role: 'dept_manager' }],
    })
    expect(payload.department_ids).toEqual(['d1', 'd2'])
    expect(payload.cost_center_ids).toEqual(['cc1'])
  })
})
