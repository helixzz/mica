import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type DeliveryAddress } from '@/api'
import { renderWithProviders, screen, waitFor } from '@/test/utils'

import { DeliveryAddressSelect } from './DeliveryAddressSelect'

vi.mock('@/api', () => ({
  api: {
    listDeliveryAddresses: vi.fn(),
    createDeliveryAddress: vi.fn(),
  },
}))

const BASE: DeliveryAddress = {
  id: 'shared',
  label: '张江机房 A 区',
  contact_name: '张伟',
  contact_phone: '138 0000 0000',
  detail: '上海市浦东新区张江高科技园区 88 号 5 层机房',
  owner_id: null,
  company_id: 'company-1',
  is_shared: true,
  usage_count: 3,
  last_used_at: '2026-10-01T00:00:00Z',
  is_active: true,
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
}

const PRIVATE: DeliveryAddress = {
  ...BASE,
  id: 'private',
  label: null,
  contact_name: '李娜',
  contact_phone: '139 0000 0000',
  detail: '北京市海淀区中关村大街 1 号',
  owner_id: 'user-1',
  is_shared: false,
}

const listMock = () => vi.mocked(api.listDeliveryAddresses)

describe('<DeliveryAddressSelect />', () => {
  beforeEach(() => {
    listMock().mockReset()
    listMock().mockResolvedValue([BASE, PRIVATE])
  })

  it('renders the name, the phone and the whole address in one option row', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DeliveryAddressSelect value={null} onChange={() => {}} />)

    await user.click(screen.getByRole('combobox'))

    expect(await screen.findByText('张伟')).toBeInTheDocument()
    expect(screen.getByText('138 0000 0000')).toBeInTheDocument()
    // The full address is in the DOM rather than clipped to a single line.
    expect(
      screen.getByText('上海市浦东新区张江高科技园区 88 号 5 层机房'),
    ).toBeInTheDocument()
    expect(screen.getByText('张江机房 A 区')).toBeInTheDocument()
  })

  it('reports the whole entry so the caller can copy its three fields', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    const onPick = vi.fn()
    renderWithProviders(
      <DeliveryAddressSelect value={null} onChange={onChange} onPick={onPick} />,
    )

    await user.click(screen.getByRole('combobox'))
    await user.click(await screen.findByText('李娜'))

    await waitFor(() => expect(onChange).toHaveBeenCalledWith('private'))
    expect(onPick).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'private',
        contact_name: '李娜',
        contact_phone: '139 0000 0000',
        detail: '北京市海淀区中关村大街 1 号',
      }),
    )
  })

  it('marks shared entries only', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DeliveryAddressSelect value={null} onChange={() => {}} />)

    await user.click(screen.getByRole('combobox'))

    const badges = await screen.findAllByText('共享')
    expect(badges).toHaveLength(1)
  })

  it('explains an empty address book instead of showing a blank panel', async () => {
    const user = userEvent.setup()
    listMock().mockResolvedValue([])
    renderWithProviders(<DeliveryAddressSelect value={null} onChange={() => {}} />)

    await user.click(screen.getByRole('combobox'))

    expect(await screen.findByText(/地址簿还没有条目/)).toBeInTheDocument()
  })

  it('reports a cleared selection as null', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    renderWithProviders(
      <DeliveryAddressSelect value="private" onChange={() => {}} onPick={onPick} />,
    )

    // The clear affordance only appears once an entry is selected.
    const clear = await screen.findByLabelText('close-circle')
    await user.click(clear)

    await waitFor(() => expect(onPick).toHaveBeenCalledWith(null))
  })
})
