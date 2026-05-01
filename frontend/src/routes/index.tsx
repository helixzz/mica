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
const DeliveryPlans = lazy(() => import('@/pages/DeliveryPlans').then((m) => ({ default: m.DeliveryPlansPage })))
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
const SsoCallbackPage = lazy(() =>
  import('@/pages/SsoCallback').then((m) => ({ default: m.SsoCallbackPage })),
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
const RFQListPage = lazy(() => import('@/pages/RFQList'))
const RFQNewPage = lazy(() => import('@/pages/RFQNew'))
const RFQDetailPage = lazy(() => import('@/pages/RFQDetail'))
const SuppliersPage = lazy(() => import('@/pages/Suppliers'))
const SupplierDetailPage = lazy(() => import('@/pages/SupplierDetail'))
const ItemDetailPage = lazy(() => import('@/pages/ItemDetail'))
const ItemsPage = lazy(() => import('@/pages/Items'))

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

function ProcurementGate({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user || user.role === 'requester') {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}

const PROCUREMENT_ROLES = ['admin', 'it_buyer', 'procurement_mgr', 'finance_auditor'] as const

function hideForRequester(children: React.ReactNode) {
  const user = useAuth.getState().user
  if (!user || user.role === 'requester') return null
  return children
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/sso-callback" element={<SsoCallbackPage />} />
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
          <Route path="/purchase-requisitions/new/:copyId" element={<PRNewPage />} />
          <Route path="/purchase-requisitions/:id/edit" element={<PREditPage />} />
          <Route path="/purchase-requisitions/:id" element={<PRDetailPage />} />
          <Route path="/purchase-orders" element={<POListPage />} />
          <Route path="/purchase-orders/:id" element={<PODetailPage />} />
          <Route path="/contracts" element={<ContractsPage />} />
          <Route path="/contracts/:id" element={<ContractDetailPage />} />
          <Route path="/shipments" element={<ProcurementGate><ShipmentsPage /></ProcurementGate>} />
          <Route path="/delivery-plans" element={<ProcurementGate><DeliveryPlans /></ProcurementGate>} />
          <Route path="/payments" element={<ProcurementGate><PaymentsPage /></ProcurementGate>} />
          <Route path="/invoices" element={<ProcurementGate><InvoicesPage /></ProcurementGate>} />
          <Route path="/invoices/:id" element={<ProcurementGate><InvoiceDetailPage /></ProcurementGate>} />
          <Route path="/sku" element={<ProcurementGate><SKUPage /></ProcurementGate>} />
          <Route path="/rfqs" element={<ProcurementGate><RFQListPage /></ProcurementGate>} />
          <Route path="/rfqs/new" element={<ProcurementGate><RFQNewPage /></ProcurementGate>} />
          <Route path="/rfqs/:id" element={<ProcurementGate><RFQDetailPage /></ProcurementGate>} />
          <Route path="/suppliers" element={<ProcurementGate><SuppliersPage /></ProcurementGate>} />
          <Route path="/suppliers/:id" element={<ProcurementGate><SupplierDetailPage /></ProcurementGate>} />
          <Route path="/items" element={<ProcurementGate><ItemsPage /></ProcurementGate>} />
          <Route path="/items/:id" element={<ProcurementGate><ItemDetailPage /></ProcurementGate>} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/search" element={<SearchResults />} />
          <Route path="/notifications" element={<NotificationCenter />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
