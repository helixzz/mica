export interface ApprovalRuleStageFormValue {
  stage_name: string
  approver_role: string
}

export interface ApprovalRuleFormValue {
  name?: string
  biz_type?: string
  amount_min?: number | null
  amount_max?: number | null
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
  priority?: number
  is_active?: boolean
  stages?: ApprovalRuleApiStage[]
}

export function createDefaultApprovalRuleForm(defaultStageName: string): ApprovalRuleFormValue {
  return {
    priority: 100,
    is_active: true,
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
    stages: (values.stages || []).map((stage, index) => ({
      stage_name: stage.stage_name,
      approver_role: stage.approver_role,
      order: index + 1,
    })),
  }
}
