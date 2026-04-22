import { Spin } from 'antd'
import { lazy, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { AppLayout } from '@/components/Layout/AppLayout'
import { useAuth } from '@/auth/useAuth'
import { getToken } from '@/api/client'

const AdminPage = lazy(() =>
  import('@/pages/Admin').then((m) => ({ default: m.AdminPage })),
)
const ApprovalsPage = lazy(() =>
  import('@/pages/Approvals').then((m) => ({ default: m.ApprovalsPage })),
)
const ContractDetailPage = lazy(() =>
  import('@/pages/ContractDetail').then((m) => ({
    default: m.ContractDetailPage,
  })),
)
const ContractsPage = lazy(() =>
  import('@/pages/Contracts').then((m) => ({ default: m.ContractsPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/Dashboard').then((m) => ({ default: m.DashboardPage })),
)
const InvoiceDetailPage = lazy(() =>
  import('@/pages/InvoiceDetail').then((m) => ({
    default: m.InvoiceDetailPage,
  })),
)
const InvoicesPage = lazy(() =>
  import('@/pages/Invoices').then((m) => ({ default: m.InvoicesPage })),
)
const LoginPage = lazy(() =>
  import('@/pages/Login').then((m) => ({ default: m.LoginPage })),
)
const NotificationCenter = lazy(() => import('@/pages/NotificationCenter'))
const PaymentsPage = lazy(() =>
  import('@/pages/Payments').then((m) => ({ default: m.PaymentsPage })),
)
const PODetailPage = lazy(() =>
  import('@/pages/PurchaseOrders/PODetail').then((m) => ({
    default: m.PODetailPage,
  })),
)
const POListPage = lazy(() =>
  import('@/pages/PurchaseOrders/POList').then((m) => ({
    default: m.POListPage,
  })),
)
const PRDetailPage = lazy(() =>
  import('@/pages/PurchaseRequisitions/PRDetail').then((m) => ({
    default: m.PRDetailPage,
  })),
)
const PREditPage = lazy(() =>
  import('@/pages/PurchaseRequisitions/PREdit').then((m) => ({
    default: m.PREditPage,
  })),
)
const PRListPage = lazy(() =>
  import('@/pages/PurchaseRequisitions/PRList').then((m) => ({
    default: m.PRListPage,
  })),
)
const PRNewPage = lazy(() =>
  import('@/pages/PurchaseRequisitions/PRNew').then((m) => ({
    default: m.PRNewPage,
  })),
)
const SearchResults = lazy(() => import('@/pages/SearchResults'))
const ShipmentsPage = lazy(() =>
  import('@/pages/Shipments').then((m) => ({ default: m.ShipmentsPage })),
)
const SKUPage = lazy(() =>
  import('@/pages/SKU').then((m) => ({ default: m.SKUPage })),
)

function PageFallback() {
  return (
    <div
      style={{
        minHeight: '60vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Spin size="large" />
    </div>
  )
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, initialized, loadMe } = useAuth()
  const loc = useLocation()

  useEffect(() => {
    if (!initialized && getToken()) void loadMe()
    if (!initialized && !getToken()) useAuth.setState({ initialized: true })
  }, [initialized, loadMe])

  if (!initialized) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: loc }} />
  return <>{children}</>
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
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
          <Route path="/purchase-requisitions/:id/edit" element={<PREditPage />} />
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
          <Route path="/notifications" element={<NotificationCenter />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
