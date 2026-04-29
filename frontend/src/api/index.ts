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

export interface LoginOptionsResponse {
  saml_enabled: boolean
  saml_login_url: string | null
}

export interface Company {
  id: string
  code: string
  name_zh: string
  name_en: string | null
  default_locale: string
  default_currency: string
  is_enabled: boolean
  is_deleted: boolean
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
  tax_number: string | null
  contact_name: string | null
  contact_phone: string | null
  contact_email: string | null
  payee_name: string | null
  payee_bank: string | null
  payee_bank_account: string | null
  notes: string | null
  is_enabled: boolean
  is_deleted: boolean
}

export interface Item {
  id: string
  code: string
  name: string
  category: string | null
  category_id: string | null
  uom: string
  specification: string | null
  requires_serial: boolean
  is_enabled: boolean
  is_deleted: boolean
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
  cost_center_id: string | null
  expense_type_id: string | null
  procurement_category_id: string | null
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
  pr_number?: string | null
  supplier_id: string
  supplier_name?: string | null
  supplier_code?: string | null
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

export interface PurchaseOrderListItem {
  id: string
  po_number: string
  pr_id: string
  pr_number?: string | null
  supplier_id: string
  supplier_name?: string | null
  supplier_code?: string | null
  status: string
  currency: string
  total_amount: string
  amount_paid: string
  amount_invoiced: string
  qty_received: string
  source_type: string
  created_at: string
  updated_at: string
}

export interface PRConversionPreviewItem {
  pr_item_id: string
  line_no: number
  item_name: string
  qty: string
  uom: string
  unit_price: string | null
  amount: string
}

export interface PRConversionPreviewGroup {
  supplier_id: string
  supplier_name: string | null
  supplier_code: string | null
  item_count: number
  subtotal: string
  items: PRConversionPreviewItem[]
}

export interface PRQuoteCandidate {
  pr_item_id: string
  line_no: number
  item_id: string
  item_name: string
  supplier_id: string
  supplier_name: string | null
  supplier_code: string | null
  unit_price: string
  currency: string
  source_ref: string
  already_exists: boolean
  already_up_to_date: boolean
}

export interface DocumentTemplate {
  id: string
  code: string
  name: string
  description: string | null
  template_document_id: string | null
  template_filename: string | null
  template_size: number | null
  filename_template: string
  is_enabled: boolean
}

export interface Contract {
  id: string
  contract_number: string
  po_id: string
  po_number?: string | null
  po_status?: string | null
  supplier_id: string
  supplier_name?: string | null
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
  linked_pos?: {
    id: string
    po_number: string
    status: string
    total_amount: string
    currency: string
  }[]
}

export interface ContractVersion {
  id: string
  contract_id: string
  version_number: number
  change_type: string
  change_reason: string | null
  change_summary: string | null
  snapshot_json: Record<string, unknown>
  changed_by_id: string | null
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
  contract_id: string | null
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
  contract_id: string | null
  contract_number?: string | null
  schedule_item_id: string | null
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
  line_type: 'product' | 'freight' | 'adjustment' | 'tax_surcharge' | 'note'
  line_no: number
  item_name: string
  qty: string
  unit_price: string
  subtotal: string
  tax_amount: string
}

export interface InvoiceAttachment {
  document_id: string
  role: string
  display_order: number
  original_filename: string
  content_type: string
  file_size: number
}

export interface Invoice {
  id: string
  internal_number: string
  invoice_number: string
  supplier_id: string
  invoice_date: string
  due_date: string | null
  subtotal: string
  tax_amount: string
  total_amount: string
  currency: string
  tax_number: string | null
  status: string
  is_fully_matched: boolean
  notes: string | null
  created_at: string
  lines: InvoiceLine[]
  attachments: InvoiceAttachment[]
}

export interface InvoiceListRow {
  id: string
  internal_number: string
  invoice_number: string
  supplier_id: string
  invoice_date: string
  subtotal: string
  tax_amount: string
  total_amount: string
  currency: string
  status: string
  is_fully_matched: boolean
  created_at: string
}

export interface InvoiceValidation {
  line_no: number
  po_item_id: string | null
  invoiced_subtotal: string
  po_remaining: string | null
  overage: string
  severity: 'ok' | 'warn' | 'error'
  message: string | null
}

export interface InvoiceCreateResponse {
  invoice: Invoice
  validations: InvoiceValidation[]
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
  biz_id: string | null
  biz_number: string | null
  biz_title: string | null
  biz_amount: number | null
  submitter_name: string | null
}

export interface FieldManifest {
  resource: string
  role: string
  fields: Record<string, boolean>
}

export interface DocumentOut {
  id: string
  original_filename: string
  content_type: string
  file_size: number
  content_hash: string
  doc_category: string
  created_at: string
}

export interface SKUPriceRecord {
  id: string
  item_id: string
  supplier_id: string | null
  price: string
  currency: string
  quotation_date: string
  source_type: string
  source_ref: string | null
  entered_by_id: string | null
  notes: string | null
}

export interface SKUBenchmark {
  item_id: string
  window_days: number
  avg_price: string
  median_price: string
  stddev: string
  min_price: string
  max_price: string
  sample_size: number
}

export interface SKUAnomaly {
  id: string
  item_id: string
  price_record_id: string | null
  baseline_avg_price: string
  observed_price: string
  deviation_pct: string
  severity: string
  status: string
  notes: string | null
}

export interface SKUTrendPoint {
  date: string
  price: string
  supplier_id: string | null
  source_type: string
}

export interface SKUPurchaseHistory {
  date: string
  supplier_name: string
  unit_price: number
  qty: number
  amount: number
  po_number: string
  deviation_pct: number | null
}

export interface SKUPurchaseStats {
  count: number
  total_qty: number
  total_amount: number
  avg_price: number | null
  median_price: number | null
  min_price: number | null
  max_price: number | null
}

export interface SKUMarketStats {
  sample_count: number
  avg_price: number
  median_price: number
  min_price: number
  max_price: number
  volatility_pct: number
  current_price: number
  current_vs_avg_pct: number
  signal: 'below_avg' | 'above_avg' | 'at_avg'
}

export interface SKUSupplierComparison {
  supplier_name: string
  avg_price: number
  count: number
  last_date: string
}

export interface SKUInsights {
  purchase_history: SKUPurchaseHistory[]
  purchase_stats: SKUPurchaseStats
  market_stats: SKUMarketStats | null
  supplier_comparison: SKUSupplierComparison[]
}

export interface ContractAttachment {
  document_id: string
  role: string
  display_order: number
  has_ocr: boolean
  ocr_chars: number
  original_filename: string
  content_type: string
  file_size: number
}

export interface ContractSearchHit {
  id: string
  contract_number: string
  title: string
  status: string
  total_amount: string
  expiry_date: string | null
  matched_in: string[]
}

export interface ContractExpiring {
  id: string
  contract_number: string
  title: string
  total_amount: string
  currency: string
  expiry_date: string | null
}

export interface TrendInfo {
  current: number
  previous: number
  direction: 'up' | 'down' | 'flat'
  delta_pct: string
}

export interface DashboardMetrics {
  pr_count: TrendInfo
  po_count: TrendInfo
  po_total_amount: TrendInfo
  pending_approvals: TrendInfo
  expiring_contracts_30d: number
  price_anomalies_pending: number
  invoices_pending_match: number
  invoices_mismatched: number
}

export interface PaymentScheduleItemInput {
  installment_no: number
  label: string
  planned_amount: number | string
  planned_date?: string | null
  trigger_type?: string
  trigger_description?: string
  notes?: string
}

export interface PaymentScheduleItem {
  id: string
  contract_id: string | null
  po_id: string | null
  installment_no: number
  label: string
  planned_amount: string
  planned_date: string | null
  trigger_type: string
  trigger_description: string | null
  status: string
  actual_amount: string | null
  actual_date: string | null
  payment_record_id: string | null
  invoice_id: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PaymentScheduleSummary {
  contract_total: string
  planned_total: string
  paid_total: string
  remaining: string
  total_mismatch: boolean
  items: PaymentScheduleItem[]
}

export interface PaymentForecastMonth {
  month: string
  planned: string
  paid: string
  remaining: string
}

export interface PaymentForecast {
  months: PaymentForecastMonth[]
  grand_planned: string
  grand_paid: string
  paid_to_date: string
  undated_planned: string
  out_of_window_planned: string
  grand_contract_remaining: string
}

export interface InvoiceForecastMonth {
  month: string
  invoiceable: string
  invoiced: string
  pending: string
}

export interface InvoiceForecast {
  months: InvoiceForecastMonth[]
  window_invoiceable: string
  window_invoiced: string
  grand_invoiceable_to_date: string
  grand_invoiced_to_date: string
  grand_pending_to_date: string
}

export interface ClassificationItem {
  id: string
  code: string
  label_zh: string
  label_en: string
  sort_order: number
  is_active: boolean
  parent_id?: string | null
  level?: number
  type?: string
}

export interface ClassificationTreeItem extends ClassificationItem {
  children: ClassificationItem[]
}

export interface ClassificationInput {
  code: string
  label_zh: string
  label_en: string
  sort_order?: number
}

export function flattenCategoryTree(tree: ClassificationTreeItem[]): ClassificationItem[] {
  const result: ClassificationItem[] = []
  for (const node of tree) {
    result.push(node)
    for (const child of node.children || []) {
      result.push(child)
    }
  }
  return result
}

export interface InvoiceExtractResult {
  invoice_number: string | null
  invoice_code: string | null
  invoice_date: string | null
  seller_name: string | null
  seller_tax_id: string | null
  buyer_name: string | null
  buyer_tax_id: string | null
  subtotal: string | null
  tax_amount: string | null
  total_amount: string | null
  currency: string
  lines: {
    item_name: string | null
    spec: string | null
    qty: string | null
    unit_price: string | null
    tax_rate: string | null
    tax_amount: string | null
    subtotal: string | null
  }[]
  raw_extract_source: string
  confidence: number
  error: string | null
}

export const api = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const { data } = await client.post<TokenResponse>('/auth/login/json', { username, password })
    return data
  },
  async loginOptions(): Promise<LoginOptionsResponse> {
    const { data } = await client.get<LoginOptionsResponse>('/auth/login-options')
    return data
  },
  async refreshSamlMetadata(): Promise<Record<string, string>> {
    const { data } = await client.post<Record<string, string>>('/saml/refresh-metadata')
    return data
  },
  async me(): Promise<User> {
    const { data } = await client.get<User>('/auth/me')
    return data
  },
  async companies(includeDisabled = false): Promise<Company[]> {
    const { data } = await client.get<Company[]>('/companies', { params: includeDisabled ? { include_disabled: true } : {} })
    return data
  },
  async createCompany(body: { code: string; name_zh: string; name_en?: string; default_currency?: string }): Promise<Company> {
    const { data } = await client.post<Company>('/companies', body)
    return data
  },
  async updateCompany(id: string, body: { name_zh?: string; name_en?: string; default_currency?: string; is_enabled?: boolean }): Promise<Company> {
    const { data } = await client.patch<Company>(`/companies/${id}`, body)
    return data
  },
  async deleteCompany(id: string): Promise<void> {
    await client.delete(`/companies/${id}`)
  },
  async listRecycleBin(): Promise<{ entity_type: string; entity_id: string; code: string; label: string; deleted_at: string | null }[]> {
    const { data } = await client.get('/admin/recycle-bin')
    return data
  },
  async restoreFromRecycleBin(entityType: string, entityId: string): Promise<void> {
    await client.post(`/admin/recycle-bin/${entityType}/${entityId}/restore`)
  },
  async departments(): Promise<Department[]> {
    const { data } = await client.get<Department[]>('/departments')
    return data
  },
  async createDepartment(body: {
    company_id: string; code: string; name_zh: string; name_en?: string | null; parent_id?: string | null;
  }): Promise<Department> {
    const { data } = await client.post<Department>('/departments', body)
    return data
  },
  async updateDepartment(id: string, body: Record<string, unknown>): Promise<Department> {
    const { data } = await client.patch<Department>(`/departments/${id}`, body)
    return data
  },
  async deleteDepartment(id: string): Promise<void> {
    await client.delete(`/departments/${id}`)
  },
  async suppliers(): Promise<Supplier[]> {
    const { data } = await client.get<Supplier[]>('/suppliers')
    return data
  },
  async createSupplier(body: {
    code: string; name: string; tax_number?: string | null;
    contact_name?: string | null; contact_phone?: string | null;
    contact_email?: string | null;
    payee_name?: string | null; payee_bank?: string | null; payee_bank_account?: string | null;
    notes?: string | null;
  }): Promise<Supplier> {
    const { data } = await client.post<Supplier>('/suppliers', body)
    return data
  },
  async updateSupplier(id: string, body: Record<string, unknown>): Promise<Supplier> {
    const { data } = await client.patch<Supplier>(`/suppliers/${id}`, body)
    return data
  },
  async deleteSupplier(id: string): Promise<void> {
    await client.delete(`/suppliers/${id}`)
  },
  async items(): Promise<Item[]> {
    const { data } = await client.get<Item[]>('/items')
    return data
  },
  async createItem(body: {
    code: string; name: string; category?: string; uom?: string;
    specification?: string; requires_serial?: boolean; category_id?: string;
  }): Promise<Item> {
    const { data } = await client.post<Item>('/items', body)
    return data
  },
  async updateItem(id: string, body: {
    name?: string; category?: string; uom?: string;
    specification?: string; requires_serial?: boolean; is_enabled?: boolean; category_id?: string;
  }): Promise<Item> {
    const { data } = await client.patch<Item>(`/items/${id}`, body)
    return data
  },
  async deleteItem(id: string): Promise<void> {
    await client.delete(`/items/${id}`)
  },
  async listPRs(): Promise<PRListItem[]> {
    const { data } = await client.get<PRListItem[]>('/purchase-requisitions')
    return data
  },
  async getPR(id: string): Promise<PurchaseRequisition> {
    const { data } = await client.get<PurchaseRequisition>(`/purchase-requisitions/${id}`)
    return data
  },
  async getPRDownstream(id: string): Promise<{
    purchase_orders: {
      id: string
      po_number: string
      status: string
      total_amount: string
      currency: string
      supplier_id: string | null
      supplier_name: string | null
      created_at: string | null
    }[]
    contracts: {
      id: string
      contract_number: string
      title: string
      status: string
      total_amount: string
      currency: string
      po_id: string
      supplier_id: string | null
      supplier_name: string | null
    }[]
  }> {
    const { data } = await client.get(`/purchase-requisitions/${id}/downstream`)
    return data as {
      purchase_orders: {
        id: string
        po_number: string
        status: string
        total_amount: string
        currency: string
        supplier_id: string | null
        supplier_name: string | null
        created_at: string | null
      }[]
      contracts: {
        id: string
        contract_number: string
        title: string
        status: string
        total_amount: string
        currency: string
        po_id: string
        supplier_id: string | null
        supplier_name: string | null
      }[]
    }
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
  async convertToPO(id: string): Promise<PurchaseOrder[]> {
    const { data } = await client.post<PurchaseOrder[]>(
      `/purchase-requisitions/${id}/convert-to-po`
    )
    return data
  },
  async previewPRConversion(id: string): Promise<PRConversionPreviewGroup[]> {
    const { data } = await client.get<PRConversionPreviewGroup[]>(
      `/purchase-requisitions/${id}/conversion-preview`
    )
    return data
  },
  async listPRQuoteCandidates(id: string): Promise<PRQuoteCandidate[]> {
    const { data } = await client.get<PRQuoteCandidate[]>(
      `/purchase-requisitions/${id}/quote-candidates`
    )
    return data
  },
  async savePRSupplierQuotes(
    id: string,
    body: { line_nos?: number[] | null } = {},
  ): Promise<{ written_count: number; skipped_unchanged_count: number }> {
    const { data } = await client.post<{ written_count: number; skipped_unchanged_count: number }>(
      `/purchase-requisitions/${id}/save-quotes`,
      body,
    )
    return data
  },
  async listPOs(): Promise<PurchaseOrderListItem[]> {
    const { data } = await client.get<PurchaseOrderListItem[]>('/purchase-orders')
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
  async getContract(contractId: string): Promise<Contract> {
    const { data } = await client.get<Contract>(`/contracts/${contractId}`)
    return data
  },
  async listContractVersions(contractId: string): Promise<ContractVersion[]> {
    const { data } = await client.get<ContractVersion[]>(`/contracts/${contractId}/versions`)
    return data
  },
  async getContractVersion(contractId: string, versionNumber: number): Promise<ContractVersion> {
    const { data } = await client.get<ContractVersion>(
      `/contracts/${contractId}/versions/${versionNumber}`,
    )
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
    contract_number?: string | null
  }): Promise<Contract> {
    const { data } = await client.post<Contract>('/contracts', payload)
    return data
  },
  async suggestContractNumber(): Promise<{ suggested_number: string }> {
    const { data } = await client.get<{ suggested_number: string }>(
      '/contracts/suggest-number',
    )
    return data
  },
  async listLinkedPos(contractId: string): Promise<{
    id: string
    po_number: string
    status: string
    total_amount: string
    amount_paid: string
    currency: string
  }[]> {
    const { data } = await client.get(`/contracts/${contractId}/linked-pos`)
    return data as {
      id: string
      po_number: string
      status: string
      total_amount: string
      amount_paid: string
      currency: string
    }[]
  },
  async linkPoContract(poId: string, contractId: string): Promise<void> {
    await client.post(`/purchase-orders/${poId}/contracts/${contractId}`)
  },
  async unlinkPoContract(poId: string, contractId: string): Promise<void> {
    await client.delete(`/purchase-orders/${poId}/contracts/${contractId}`)
  },
  async updateContract(
    contractId: string,
    payload: {
      title?: string
      total_amount?: number | string
      signed_date?: string | null
      effective_date?: string | null
      expiry_date?: string | null
      notes?: string | null
      change_reason?: string | null
      change_summary?: string | null
    },
  ): Promise<Contract> {
    const { data } = await client.patch<Contract>(`/contracts/${contractId}`, payload)
    return data
  },
  async deleteContract(contractId: string): Promise<void> {
    await client.delete(`/contracts/${contractId}`)
  },
  async updateContractStatus(
    contractId: string,
    status: 'active' | 'superseded' | 'terminated' | 'expired',
    reason?: string | null,
  ): Promise<Contract> {
    const { data } = await client.patch<Contract>(`/contracts/${contractId}/status`, {
      status,
      reason,
    })
    return data
  },
  async listShipments(opts?: { po_id?: string; contract_id?: string }): Promise<Shipment[]> {
    const { data } = await client.get<Shipment[]>('/shipments', { params: opts })
    return data
  },
  async createShipment(payload: {
    po_id: string
    contract_id?: string | null
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
  async updateShipment(id: string, body: Record<string, unknown>): Promise<Shipment> {
    const { data } = await client.patch<Shipment>(`/shipments/${id}`, body)
    return data
  },
  async deleteShipment(id: string): Promise<void> {
    await client.delete(`/shipments/${id}`)
  },
  async listShipmentAttachments(shipmentId: string): Promise<{ document_id: string; role: string; original_filename: string; content_type: string; file_size: number; created_at: string }[]> {
    const { data } = await client.get(`/shipments/${shipmentId}/attachments`)
    return data as any
  },
  async attachShipmentDocument(shipmentId: string, documentId: string, role = 'attachment'): Promise<void> {
    await client.post(`/shipments/${shipmentId}/attachments`, { document_id: documentId, role })
  },
  async removeShipmentAttachment(shipmentId: string, documentId: string): Promise<void> {
    await client.delete(`/shipments/${shipmentId}/attachments/${documentId}`)
  },
  async listPayments(po_id?: string): Promise<PaymentRecord[]> {
    const { data } = await client.get<PaymentRecord[]>('/payments', { params: { po_id } })
    return data
  },
  async createPayment(payload: {
    po_id: string
    contract_id: string
    schedule_item_id?: string | null
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
  async updatePayment(
    id: string,
    payload: {
      amount?: number | string
      due_date?: string | null
      payment_date?: string | null
      payment_method?: string
      transaction_ref?: string | null
      notes?: string | null
    },
  ): Promise<PaymentRecord> {
    const { data } = await client.patch<PaymentRecord>(`/payments/${id}`, payload)
    return data
  },
  async deletePayment(id: string): Promise<void> {
    await client.delete(`/payments/${id}`)
  },
  async confirmPayment(id: string, payload: { payment_date?: string | null; transaction_ref?: string | null }): Promise<PaymentRecord> {
    const { data } = await client.post<PaymentRecord>(`/payments/${id}/confirm`, payload)
    return data
  },
  async listInvoices(po_id?: string): Promise<InvoiceListRow[]> {
    const { data } = await client.get<InvoiceListRow[]>('/invoices', { params: { po_id } })
    return data
  },
  async getInvoice(id: string): Promise<Invoice> {
    const { data } = await client.get<Invoice>(`/invoices/${id}`)
    return data
  },
  async createInvoice(payload: {
    supplier_id: string
    invoice_number: string
    invoice_date: string
    tax_number?: string | null
    due_date?: string | null
    notes?: string | null
    attachment_document_ids: string[]
    lines: {
      po_item_id?: string | null
      line_type?: 'product' | 'freight' | 'adjustment' | 'tax_surcharge' | 'note'
      item_name: string
      qty: number
      unit_price: number
      tax_amount?: number
    }[]
  }): Promise<InvoiceCreateResponse> {
    const { data } = await client.post<InvoiceCreateResponse>('/invoices', payload)
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
  async uploadDocument(file: File, category = 'invoice'): Promise<DocumentOut> {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('category', category)
    const { data } = await client.post<DocumentOut>('/documents/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  async getDocumentDownloadUrl(document_id: string): Promise<{ download_url: string; expires_in: number }> {
    const { data } = await client.get<{ download_url: string; expires_in: number }>(
      `/documents/${document_id}/token`
    )
    return data
  },
  async extractInvoice(document_id: string): Promise<InvoiceExtractResult> {
    const { data } = await client.post<InvoiceExtractResult>(
      `/ai/invoice-extract?document_id=${document_id}`
    )
    return data
  },
  async adminSystemInfo(): Promise<Record<string, unknown>> {
    const { data } = await client.get('/admin/system')
    return data as Record<string, unknown>
  },
  async adminListAIModels(): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/ai-models')
    return data as Record<string, unknown>[]
  },
  async adminCreateAIModel(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await client.post('/admin/ai-models', body)
    return data as Record<string, unknown>
  },
  async adminUpdateAIModel(id: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await client.patch(`/admin/ai-models/${id}`, body)
    return data as Record<string, unknown>
  },
  async adminDeleteAIModel(id: string): Promise<void> {
    await client.delete(`/admin/ai-models/${id}`)
  },
  async adminTestAIModel(id: string): Promise<{ success: boolean; model_response?: string; latency_ms: number; error?: string }> {
    const { data } = await client.post(`/admin/ai-models/${id}/test-connection`)
    return data as { success: boolean; model_response?: string; latency_ms: number; error?: string }
  },
  async adminListRoutings(): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/ai-routings')
    return data as Record<string, unknown>[]
  },
  async adminUpsertRouting(feature_code: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await client.put(`/admin/ai-routings/${feature_code}`, body)
    return data as Record<string, unknown>
  },
  async adminListUsers(): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/users')
    return data as Record<string, unknown>[]
  },
  async adminCreateUser(body: {
    username: string
    email: string
    display_name: string
    password: string
    role: string
    company_id: string
    department_id?: string | null
    cost_center_ids?: string[]
    department_ids?: string[]
    preferred_locale?: string
  }): Promise<Record<string, unknown>> {
    const { data } = await client.post('/admin/users', body)
    return data as Record<string, unknown>
  },
  async adminUpdateUser(userId: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await client.patch(`/admin/users/${userId}`, body)
    return data as Record<string, unknown>
  },
  async adminResetPassword(userId: string, newPassword: string): Promise<void> {
    await client.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword })
  },
  async adminDeleteUser(userId: string): Promise<void> {
    await client.delete(`/admin/users/${userId}`)
  },
  async adminListDocumentTemplates(): Promise<DocumentTemplate[]> {
    const { data } = await client.get<DocumentTemplate[]>('/admin/document-templates')
    return data
  },
  async adminUpdateDocumentTemplate(
    id: string,
    body: {
      name?: string
      description?: string | null
      filename_template?: string
      is_enabled?: boolean
    },
  ): Promise<DocumentTemplate> {
    const { data } = await client.patch<DocumentTemplate>(
      `/admin/document-templates/${id}`,
      body,
    )
    return data
  },
  async adminUploadDocumentTemplate(id: string, file: File): Promise<DocumentTemplate> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await client.post<DocumentTemplate>(
      `/admin/document-templates/${id}/upload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },
  async previewTemplatePlaceholders(
    id: string,
  ): Promise<{ placeholders: string[] }> {
    const { data } = await client.get<{ placeholders: string[] }>(
      `/document-templates/${id}/placeholders`,
    )
    return data
  },
  async generateScheduleDocument(
    scheduleItemId: string,
    templateCode: string,
  ): Promise<{ blob: Blob; filename: string }> {
    const formData = new FormData()
    formData.append('template_code', templateCode)
    const response = await client.post(
      `/payment-schedule-items/${scheduleItemId}/generate-document`,
      formData,
      { responseType: 'blob' },
    )
    const disposition = response.headers['content-disposition'] as string | undefined
    let filename = 'generated.docx'
    if (disposition) {
      const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
      if (utf8Match) {
        try {
          filename = decodeURIComponent(utf8Match[1])
        } catch {
          filename = utf8Match[1]
        }
      } else {
        const match = disposition.match(/filename="?([^";]+)"?/i)
        if (match) filename = decodeURIComponent(match[1])
      }
    }
    return { blob: response.data as Blob, filename }
  },
  async adminAuditLogs(params: { since_days?: number; event_type_prefix?: string } = {}): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/audit-logs', { params })
    return data as Record<string, unknown>[]
  },
  async adminAICallLogs(params: { since_days?: number; feature_code?: string } = {}): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/ai-call-logs', { params })
    return data as Record<string, unknown>[]
  },
  async adminAICallStats(since_days = 7): Promise<Record<string, unknown>[]> {
    const { data } = await client.get('/admin/ai-call-stats', { params: { since_days } })
    return data as Record<string, unknown>[]
  },
  async recordSKUPrice(body: {
    item_id: string
    price: number
    quotation_date: string
    supplier_id?: string | null
    source_type?: string
    source_ref?: string | null
    notes?: string | null
  }): Promise<{ record: SKUPriceRecord; anomaly: SKUAnomaly | null }> {
    const { data } = await client.post('/sku/prices', body)
    return data as { record: SKUPriceRecord; anomaly: SKUAnomaly | null }
  },
  async listSKUPrices(item_id?: string): Promise<SKUPriceRecord[]> {
    const { data } = await client.get<SKUPriceRecord[]>('/sku/prices', { params: { item_id } })
    return data
  },
  async getSKUBenchmark(item_id: string, window_days = 90): Promise<SKUBenchmark | null> {
    const { data } = await client.get<SKUBenchmark | null>(`/sku/benchmarks/${item_id}`, {
      params: { window_days },
    })
    return data
  },
  async getSKUTrend(item_id: string, days = 180): Promise<SKUTrendPoint[]> {
    const { data } = await client.get<SKUTrendPoint[]>(`/sku/trend/${item_id}`, { params: { days } })
    return data
  },
  async listSKUAnomalies(status?: string): Promise<SKUAnomaly[]> {
    const { data } = await client.get<SKUAnomaly[]>('/sku/anomalies', { params: { status } })
    return data
  },
  async getSKUInsights(itemId: string, windowDays = 365): Promise<SKUInsights> {
    const { data } = await client.get<SKUInsights>(`/sku/insights/${itemId}`, {
      params: { window_days: windowDays },
    })
    return data
  },
  async acknowledgeAnomaly(id: string, notes?: string): Promise<SKUAnomaly> {
    const { data } = await client.post<SKUAnomaly>(`/sku/anomalies/${id}/acknowledge`, { notes })
    return data
  },
  async attachContractDocument(contract_id: string, document_id: string, run_ocr = true) {
    const { data } = await client.post(`/contracts/${contract_id}/attachments`, {
      document_id,
      role: 'scan',
      run_ocr,
    })
    return data
  },
  async listContractAttachments(contract_id: string): Promise<ContractAttachment[]> {
    const { data } = await client.get<ContractAttachment[]>(`/contracts/${contract_id}/attachments`)
    return data
  },
  async getContractAttachmentOcr(
    contract_id: string,
    document_id: string,
  ): Promise<{ contract_id: string; document_id: string; has_ocr: boolean; ocr_chars: number; ocr_text: string }> {
    const { data } = await client.get<{
      contract_id: string
      document_id: string
      has_ocr: boolean
      ocr_chars: number
      ocr_text: string
    }>(`/contracts/${contract_id}/attachments/${document_id}/ocr`)
    return data
  },
  async searchContracts(q: string): Promise<ContractSearchHit[]> {
    const { data } = await client.get<ContractSearchHit[]>('/contracts-search', { params: { q } })
    return data
  },
  async listExpiringContracts(within_days = 30): Promise<ContractExpiring[]> {
    const { data } = await client.get<ContractExpiring[]>('/contracts-expiring', {
      params: { within_days },
    })
    return data
  },
  async getDashboardMetrics(
    compare_to: 'last_month' | 'last_week' = 'last_month',
  ): Promise<DashboardMetrics> {
    const { data } = await client.get<DashboardMetrics>('/dashboard/metrics', {
      params: { compare_to },
    })
    return data
  },
  async getPaymentSchedule(contractId: string): Promise<PaymentScheduleSummary> {
    const { data } = await client.get<PaymentScheduleSummary>(
      `/contracts/${contractId}/payment-schedule`,
    )
    return data
  },
  async createPaymentSchedule(
    contractId: string,
    items: PaymentScheduleItemInput[],
  ): Promise<PaymentScheduleItem[]> {
    const { data } = await client.post<PaymentScheduleItem[]>(
      `/contracts/${contractId}/payment-schedule`,
      { items },
    )
    return data
  },
  async executeScheduleItem(
    contractId: string,
    installmentNo: number,
    body: { payment_method: string; transaction_ref?: string; invoice_id?: string; amount?: number },
  ): Promise<PaymentScheduleItem> {
    const { data } = await client.post<PaymentScheduleItem>(
      `/contracts/${contractId}/payment-schedule/${installmentNo}/execute`,
      body,
    )
    return data
  },
  async deleteScheduleItem(contractId: string, installmentNo: number): Promise<void> {
    await client.delete(`/contracts/${contractId}/payment-schedule/${installmentNo}`)
  },
  async updateScheduleItem(
    contractId: string,
    installmentNo: number,
    body: {
      label?: string
      planned_amount?: number | string
      planned_date?: string | null
      trigger_type?: string
      trigger_description?: string | null
    },
  ): Promise<PaymentScheduleItem> {
    const { data } = await client.put<PaymentScheduleItem>(
      `/contracts/${contractId}/payment-schedule/${installmentNo}`,
      body,
    )
    return data
  },
  async getPOPaymentSchedule(poId: string): Promise<PaymentScheduleSummary> {
    const { data } = await client.get<PaymentScheduleSummary>(
      `/purchase-orders/${poId}/payment-schedule`,
    )
    return data
  },
  async createPOPaymentSchedule(
    poId: string,
    items: PaymentScheduleItemInput[],
  ): Promise<PaymentScheduleItem[]> {
    const { data } = await client.post<PaymentScheduleItem[]>(
      `/purchase-orders/${poId}/payment-schedule`,
      { items },
    )
    return data
  },
  async executePOScheduleItem(
    poId: string,
    installmentNo: number,
    body: { payment_method: string; transaction_ref?: string; invoice_id?: string; amount?: number },
  ): Promise<PaymentScheduleItem> {
    const { data } = await client.post<PaymentScheduleItem>(
      `/purchase-orders/${poId}/payment-schedule/${installmentNo}/execute`,
      body,
    )
    return data
  },
  async deletePOScheduleItem(poId: string, installmentNo: number): Promise<void> {
    await client.delete(`/purchase-orders/${poId}/payment-schedule/${installmentNo}`)
  },
  async updatePOScheduleItem(
    poId: string,
    installmentNo: number,
    body: {
      label?: string
      planned_amount?: number | string
      planned_date?: string | null
      trigger_type?: string
      trigger_description?: string | null
    },
  ): Promise<PaymentScheduleItem> {
    const { data } = await client.put<PaymentScheduleItem>(
      `/purchase-orders/${poId}/payment-schedule/${installmentNo}`,
      body,
    )
    return data
  },
  async getPaymentForecast(
    opts: { months?: number; past_months?: number; anchor?: string } = {},
  ): Promise<PaymentForecast> {
    const { months = 6, past_months, anchor } = opts
    const { data } = await client.get<PaymentForecast>('/dashboard/payment-forecast', {
      params: {
        months,
        ...(past_months !== undefined ? { past_months } : {}),
        ...(anchor ? { anchor } : {}),
      },
    })
    return data
  },
  async getInvoiceForecast(
    opts: { months?: number; past_months?: number; anchor?: string } = {},
  ): Promise<InvoiceForecast> {
    const { months = 6, past_months, anchor } = opts
    const { data } = await client.get<InvoiceForecast>('/dashboard/invoice-forecast', {
      params: {
        months,
        ...(past_months !== undefined ? { past_months } : {}),
        ...(anchor ? { anchor } : {}),
      },
    })
    return data
  },
  async listCostCenters(includeDisabled = false): Promise<ClassificationItem[]> {
    const { data } = await client.get<ClassificationItem[]>('/cost-centers', { params: includeDisabled ? { enabled_only: false } : {} })
    return data
  },
  async listProcurementCategories(): Promise<ClassificationItem[]> {
    const { data } = await client.get<ClassificationItem[]>('/procurement-categories')
    return data
  },
  async getCategoryTree(): Promise<ClassificationTreeItem[]> {
    const { data } = await client.get<ClassificationTreeItem[]>('/procurement-categories/tree')
    return data
  },
  async listLookupValues(type: string): Promise<ClassificationItem[]> {
    const { data } = await client.get<ClassificationItem[]>('/lookup-values', { params: { type } })
    return data
  },
  async createCostCenter(body: ClassificationInput): Promise<ClassificationItem> {
    const { data } = await client.post<ClassificationItem>('/admin/cost-centers', body)
    return data
  },
  async updateCostCenter(id: string, body: Record<string, unknown>): Promise<ClassificationItem> {
    const { data } = await client.put<ClassificationItem>(`/admin/cost-centers/${id}`, body)
    return data
  },
  async deleteCostCenter(id: string): Promise<void> {
    await client.delete(`/admin/cost-centers/${id}`)
  },
  async createProcurementCategory(body: ClassificationInput & { parent_id?: string }): Promise<ClassificationItem> {
    const { data } = await client.post<ClassificationItem>('/admin/procurement-categories', body)
    return data
  },
  async deleteProcurementCategory(id: string): Promise<void> {
    await client.delete(`/admin/procurement-categories/${id}`)
  },
  async updateProcurementCategory(id: string, body: Record<string, unknown>): Promise<ClassificationItem> {
    const { data } = await client.put<ClassificationItem>(`/admin/procurement-categories/${id}`, body)
    return data
  },
  async createLookupValue(body: ClassificationInput & { type: string }): Promise<ClassificationItem> {
    const { data } = await client.post<ClassificationItem>('/admin/lookup-values', body)
    return data
  },
  async updateLookupValue(id: string, body: Record<string, unknown>): Promise<ClassificationItem> {
    const { data } = await client.put<ClassificationItem>(`/admin/lookup-values/${id}`, body)
    return data
  },
  async deleteLookupValue(id: string): Promise<void> {
    await client.delete(`/admin/lookup-values/${id}`)
  },
  async adminUploadFile(endpoint: string, formData: FormData): Promise<{ data: any }> {
    return client.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  async adminListApprovalRules(): Promise<any[]> {
    const { data } = await client.get('/approval-rules')
    return data
  },
  async adminCreateApprovalRule(body: any): Promise<any> {
    const { data } = await client.post('/approval-rules', body)
    return data
  },
  async adminUpdateApprovalRule(id: string, body: any): Promise<any> {
    const { data } = await client.put(`/approval-rules/${id}`, body)
    return data
  },
  async adminDeleteApprovalRule(id: string): Promise<void> {
    await client.delete(`/approval-rules/${id}`)
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
