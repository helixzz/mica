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
  requires_serial: boolean
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
  qty_received: string
  qty_invoiced: string
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
  qty_received: string
  amount_paid: string
  amount_invoiced: string
  source_type: string
  source_ref: string | null
  created_by_id: string
  created_at: string
  updated_at: string
  items: POItem[]
}

export interface Contract {
  id: string
  contract_number: string
  po_id: string
  supplier_id: string
  title: string
  current_version: number
  status: string
  currency: string
  total_amount: string
  signed_date: string | null
  effective_date: string | null
  expiry_date: string | null
  notes: string | null
  created_at: string
}

export interface ShipmentItem {
  id: string
  po_item_id: string
  line_no: number
  item_name: string
  qty_shipped: string
  qty_received: string
  unit_price: string
}

export interface Shipment {
  id: string
  shipment_number: string
  po_id: string
  batch_no: number
  is_default: boolean
  status: string
  carrier: string | null
  tracking_number: string | null
  expected_date: string | null
  actual_date: string | null
  notes: string | null
  created_at: string
  items: ShipmentItem[]
}

export interface PaymentRecord {
  id: string
  payment_number: string
  po_id: string
  installment_no: number
  amount: string
  currency: string
  due_date: string | null
  payment_date: string | null
  payment_method: string
  transaction_ref: string | null
  status: string
  notes: string | null
  created_at: string
}

export interface InvoiceLine {
  id: string
  po_item_id: string | null
  line_no: number
  item_name: string
  qty: string
  unit_price: string
  amount: string
}

export interface Invoice {
  id: string
  internal_number: string
  invoice_number: string
  po_id: string
  supplier_id: string
  invoice_date: string
  due_date: string | null
  subtotal: string
  tax_amount: string
  total_amount: string
  currency: string
  tax_number: string | null
  status: string
  notes: string | null
  created_at: string
  lines: InvoiceLine[]
}

export interface POProgress {
  po_id: string
  po_number: string
  total_amount: string
  amount_paid: string
  amount_invoiced: string
  total_qty: string
  qty_received: string
  qty_invoiced: string
  pct_received: number
  pct_invoiced: number
  pct_paid: number
}

export interface ApprovalTask {
  id: string
  instance_id: string
  stage_order: number
  stage_name: string
  assignee_id: string
  assignee_role: string | null
  status: string
  action: string | null
  comment: string | null
  assigned_at: string
  acted_at: string | null
}

export interface FieldManifest {
  resource: string
  role: string
  fields: Record<string, boolean>
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
  async getPOProgress(id: string): Promise<POProgress> {
    const { data } = await client.get<POProgress>(`/purchase-orders/${id}/progress`)
    return data
  },
  async listContracts(po_id?: string): Promise<Contract[]> {
    const { data } = await client.get<Contract[]>('/contracts', { params: { po_id } })
    return data
  },
  async createContract(payload: {
    po_id: string
    title: string
    total_amount: number | string
    signed_date?: string | null
    effective_date?: string | null
    expiry_date?: string | null
    notes?: string | null
  }): Promise<Contract> {
    const { data } = await client.post<Contract>('/contracts', payload)
    return data
  },
  async listShipments(po_id?: string): Promise<Shipment[]> {
    const { data } = await client.get<Shipment[]>('/shipments', { params: { po_id } })
    return data
  },
  async createShipment(payload: {
    po_id: string
    items: { po_item_id: string; qty_shipped: number; qty_received?: number }[]
    carrier?: string | null
    tracking_number?: string | null
    expected_date?: string | null
    actual_date?: string | null
    notes?: string | null
  }): Promise<Shipment> {
    const { data } = await client.post<Shipment>('/shipments', payload)
    return data
  },
  async listPayments(po_id?: string): Promise<PaymentRecord[]> {
    const { data } = await client.get<PaymentRecord[]>('/payments', { params: { po_id } })
    return data
  },
  async createPayment(payload: {
    po_id: string
    amount: number | string
    due_date?: string | null
    payment_date?: string | null
    payment_method?: string
    transaction_ref?: string | null
    notes?: string | null
  }): Promise<PaymentRecord> {
    const { data } = await client.post<PaymentRecord>('/payments', payload)
    return data
  },
  async confirmPayment(id: string, payload: { payment_date?: string | null; transaction_ref?: string | null }): Promise<PaymentRecord> {
    const { data } = await client.post<PaymentRecord>(`/payments/${id}/confirm`, payload)
    return data
  },
  async listInvoices(po_id?: string): Promise<Invoice[]> {
    const { data } = await client.get<Invoice[]>('/invoices', { params: { po_id } })
    return data
  },
  async createInvoice(payload: {
    po_id: string
    invoice_number: string
    invoice_date: string
    tax_amount?: number | string
    tax_number?: string | null
    due_date?: string | null
    notes?: string | null
    lines: { po_item_id?: string | null; item_name: string; qty: number; unit_price: number }[]
  }): Promise<Invoice> {
    const { data } = await client.post<Invoice>('/invoices', payload)
    return data
  },
  async myPendingApprovals(): Promise<ApprovalTask[]> {
    const { data } = await client.get<ApprovalTask[]>('/approval/pending')
    return data
  },
  async fieldManifest(resource: string): Promise<FieldManifest> {
    const { data } = await client.get<FieldManifest>(`/authz/field-manifest/${resource}`)
    return data
  },
  async aiStream(
    feature_code: 'pr_description_polish' | 'sku_suggest',
    body: { draft?: string; query?: string },
    onChunk: (chunk: string) => void,
    onDone?: () => void,
    signal?: AbortSignal
  ): Promise<void> {
    const token = localStorage.getItem('mica.token')
    const res = await fetch('/api/v1/ai/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ feature_code, ...body }),
      signal,
    })
    if (!res.body) {
      onDone?.()
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const lines = part.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6)
            if (payload === '[DONE]') {
              onDone?.()
              return
            }
            onChunk(payload)
          }
        }
      }
    }
    onDone?.()
  },
}
