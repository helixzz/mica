import { Spin } from 'antd'
import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { AppLayout } from '@/components/Layout/AppLayout'
import { AdminPage } from '@/pages/Admin'
import { ApprovalsPage } from '@/pages/Approvals'
import { ContractDetailPage } from '@/pages/ContractDetail'
import { ContractsPage } from '@/pages/Contracts'
import { DashboardPage } from '@/pages/Dashboard'
import { InvoiceDetailPage } from '@/pages/InvoiceDetail'
import { InvoicesPage } from '@/pages/Invoices'
import { LoginPage } from '@/pages/Login'
import { PaymentsPage } from '@/pages/Payments'
import { PODetailPage } from '@/pages/PurchaseOrders/PODetail'
import { POListPage } from '@/pages/PurchaseOrders/POList'
import { PRDetailPage } from '@/pages/PurchaseRequisitions/PRDetail'
import { PRListPage } from '@/pages/PurchaseRequisitions/PRList'
import { PRNewPage } from '@/pages/PurchaseRequisitions/PRNew'
import { ShipmentsPage } from '@/pages/Shipments'
import { SKUPage } from '@/pages/SKU'
import { useAuth } from '@/auth/useAuth'
import { getToken } from '@/api/client'
import SearchResults from '@/pages/SearchResults'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, initialized, loadMe } = useAuth()
  const loc = useLocation()

  useEffect(() => {
    if (!initialized && getToken()) void loadMe()
    if (!initialized && !getToken()) useAuth.setState({ initialized: true })
  }, [initialized, loadMe])

  if (!initialized) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: loc }} />
  return <>{children}</>
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/purchase-requisitions" element={<PRListPage />} />
        <Route path="/purchase-requisitions/new" element={<PRNewPage />} />
        <Route path="/purchase-requisitions/:id" element={<PRDetailPage />} />
        <Route path="/purchase-orders" element={<POListPage />} />
        <Route path="/purchase-orders/:id" element={<PODetailPage />} />
        <Route path="/contracts" element={<ContractsPage />} />
        <Route path="/contracts/:id" element={<ContractDetailPage />} />
        <Route path="/shipments" element={<ShipmentsPage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
        <Route path="/sku" element={<SKUPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/search" element={<SearchResults />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
