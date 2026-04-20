import { client } from './client'

export interface User {
  id: string
  username: string
  email: string
  display_name: string
  role: string
  company_id: string
  department_id: string | null
  preferred_locale: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface Company {
  id: string
  code: string
  name_zh: string
  name_en: string | null
  default_locale: string
  default_currency: string
}

export interface Department {
  id: string
  company_id: string
  code: string
  name_zh: string
  name_en: string | null
}

export interface Supplier {
  id: string
  code: string
  name: string
  contact_name: string | null
  contact_phone: string | null
  contact_email: string | null
}

export interface Item {
  id: string
  code: string
  name: string
  category: string | null
  uom: string
  specification: string | null
}

export interface PRItem {
  id?: string
  line_no: number
  item_id: string | null
  item_name: string
  specification: string | null
  supplier_id: string | null
  qty: number | string
  uom: string
  unit_price: number | string
  amount?: number | string
}

export interface PurchaseRequisition {
  id: string
  pr_number: string
  title: string
  business_reason: string | null
  status: string
  requester_id: string
  company_id: string
  department_id: string | null
  currency: string
  total_amount: string
  required_date: string | null
  submitted_at: string | null
  decided_at: string | null
  decided_by_id: string | null
  decision_comment: string | null
  created_at: string
  updated_at: string
  items: PRItem[]
}

export interface PRListItem {
  id: string
  pr_number: string
  title: string
  status: string
  requester_id: string
  currency: string
  total_amount: string
  submitted_at: string | null
  created_at: string
}

export interface POItem {
  id: string
  line_no: number
  item_id: string | null
  item_name: string
  specification: string | null
  qty: string
  uom: string
  unit_price: string
  amount: string
}

export interface PurchaseOrder {
  id: string
  po_number: string
  pr_id: string
  supplier_id: string
  company_id: string
  status: string
  currency: string
  total_amount: string
  source_type: string
  source_ref: string | null
  created_by_id: string
  created_at: string
  updated_at: string
  items: POItem[]
}

export const api = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const { data } = await client.post<TokenResponse>('/auth/login/json', { username, password })
    return data
  },
  async me(): Promise<User> {
    const { data } = await client.get<User>('/auth/me')
    return data
  },
  async companies(): Promise<Company[]> {
    const { data } = await client.get<Company[]>('/companies')
    return data
  },
  async departments(): Promise<Department[]> {
    const { data } = await client.get<Department[]>('/departments')
    return data
  },
  async suppliers(): Promise<Supplier[]> {
    const { data } = await client.get<Supplier[]>('/suppliers')
    return data
  },
  async items(): Promise<Item[]> {
    const { data } = await client.get<Item[]>('/items')
    return data
  },
  async listPRs(): Promise<PRListItem[]> {
    const { data } = await client.get<PRListItem[]>('/purchase-requisitions')
    return data
  },
  async getPR(id: string): Promise<PurchaseRequisition> {
    const { data } = await client.get<PurchaseRequisition>(`/purchase-requisitions/${id}`)
    return data
  },
  async createPR(payload: {
    title: string
    business_reason?: string
    department_id?: string | null
    currency: string
    required_date?: string | null
    items: PRItem[]
  }): Promise<PurchaseRequisition> {
    const { data } = await client.post<PurchaseRequisition>('/purchase-requisitions', payload)
    return data
  },
  async updatePR(id: string, payload: Partial<{ items: PRItem[]; title: string }>) {
    const { data } = await client.patch<PurchaseRequisition>(`/purchase-requisitions/${id}`, payload)
    return data
  },
  async submitPR(id: string): Promise<PurchaseRequisition> {
    const { data } = await client.post<PurchaseRequisition>(`/purchase-requisitions/${id}/submit`)
    return data
  },
  async decidePR(
    id: string,
    action: 'approve' | 'reject' | 'return',
    comment?: string
  ): Promise<PurchaseRequisition> {
    const { data } = await client.post<PurchaseRequisition>(
      `/purchase-requisitions/${id}/decide`,
      { action, comment }
    )
    return data
  },
  async convertToPO(id: string): Promise<PurchaseOrder> {
    const { data } = await client.post<PurchaseOrder>(
      `/purchase-requisitions/${id}/convert-to-po`
    )
    return data
  },
  async listPOs(): Promise<PurchaseOrder[]> {
    const { data } = await client.get<PurchaseOrder[]>('/purchase-orders')
    return data
  },
  async getPO(id: string): Promise<PurchaseOrder> {
    const { data } = await client.get<PurchaseOrder>(`/purchase-orders/${id}`)
    return data
  },
}
