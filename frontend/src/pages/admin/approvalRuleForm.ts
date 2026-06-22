export interface ApprovalRuleStageFormValue {
  stage_name: string
  approver_role: string
}

export interface ApprovalRuleFormValue {
  name?: string
  biz_type?: string
  amount_min?: number | null
  amount_max?: number | null
  department_ids?: string[] | null
  cost_center_ids?: string[] | null
  priority?: number
  is_active?: boolean
  stages?: ApprovalRuleStageFormValue[]
}

export interface ApprovalRuleApiStage {
  stage_name: string
  approver_role: string
  order?: number
}

export interface ApprovalRuleApiValue {
  id?: string
  name?: string
  biz_type?: string
  amount_min?: number | null
  amount_max?: number | null
  department_ids?: string[] | null
  cost_center_ids?: string[] | null
  priority?: number
  is_active?: boolean
  stages?: ApprovalRuleApiStage[]
}

export function createDefaultApprovalRuleForm(defaultStageName: string): ApprovalRuleFormValue {
  return {
    priority: 100,
    is_active: true,
    department_ids: null,
    cost_center_ids: null,
    stages: [{ stage_name: defaultStageName, approver_role: 'dept_manager' }],
  }
}

export function mapApprovalRuleToForm(
  rule: ApprovalRuleApiValue,
  defaultStageName: string,
): ApprovalRuleFormValue {
  return {
    name: rule.name,
    biz_type: rule.biz_type,
    amount_min: rule.amount_min ?? null,
    amount_max: rule.amount_max ?? null,
    department_ids: rule.department_ids ?? null,
    cost_center_ids: rule.cost_center_ids ?? null,
    priority: rule.priority,
    is_active: rule.is_active,
    stages:
      Array.isArray(rule.stages) && rule.stages.length > 0
        ? rule.stages
            .slice()
            .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
            .map((stage) => ({
              stage_name: stage.stage_name,
              approver_role: stage.approver_role,
            }))
        : createDefaultApprovalRuleForm(defaultStageName).stages,
  }
}

export function mapApprovalRuleFormToPayload(values: ApprovalRuleFormValue) {
  return {
    ...values,
    department_ids:
      values.department_ids && values.department_ids.length > 0 ? values.department_ids : null,
    cost_center_ids:
      values.cost_center_ids && values.cost_center_ids.length > 0 ? values.cost_center_ids : null,
    stages: (values.stages || []).map((stage, index) => ({
      stage_name: stage.stage_name,
      approver_role: stage.approver_role,
      order: index + 1,
    })),
  }
}
