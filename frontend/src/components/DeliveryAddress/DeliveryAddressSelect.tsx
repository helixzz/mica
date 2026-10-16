import { PlusOutlined } from '@ant-design/icons'
import { Button, Divider, Select, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DeliveryAddress } from '@/api'
import { MonoNum } from '@/components/ui'

import { DeliveryAddressModal } from './DeliveryAddressModal'

export interface DeliveryAddressSelectProps {
  /** Bound to ``delivery_address_id`` by the enclosing ``Form.Item``. */
  value?: string | null
  onChange?: (addressId: string | null) => void
  /** Receives the picked entry so the caller can copy its three text fields. */
  onPick?: (address: DeliveryAddress | null) => void
  disabled?: boolean
  /** Whether this user may create company-wide entries. */
  canMaintainShared?: boolean
  style?: React.CSSProperties
}

interface AddressSelectOption {
  value: string
  label: string
  address: DeliveryAddress
}

function AddressOptionRow({ address, sharedLabel }: { address: DeliveryAddress; sharedLabel: string }) {
  return (
    <div className="address-option">
      <div className="address-option__head">
        <span className="address-option__name">
          {address.contact_name}
          {address.label ? <span className="address-option__label">{address.label}</span> : null}
          {address.is_shared ? <span className="address-option__shared">{sharedLabel}</span> : null}
        </span>
        <MonoNum className="address-option__phone">{address.contact_phone}</MonoNum>
      </div>
      <div className="address-option__detail" title={address.detail}>
        {address.detail}
      </div>
    </div>
  )
}

/**
 * Delivery address picker: choose a saved entry, or leave it empty and type the
 * three fields by hand.
 *
 * ``options[].label`` is a plain one-line string because it drives both the
 * fuzzy search and the closed selector; the three-line layout lives entirely in
 * ``optionRender``. Picking an entry reports the *entry*, not just its id, so
 * the caller copies the text into the requisition and keeps it editable.
 */
export function DeliveryAddressSelect({
  value,
  onChange,
  onPick,
  disabled,
  canMaintainShared = false,
  style,
}: DeliveryAddressSelectProps) {
  const { t } = useTranslation()
  const [addresses, setAddresses] = useState<DeliveryAddress[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setAddresses(await api.listDeliveryAddresses())
    } catch {
      // A failed address-book load must never block a hand-typed address.
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const options = useMemo<AddressSelectOption[]>(
    () =>
      addresses.map((a) => ({
        value: a.id,
        label: `${a.contact_name} · ${a.detail}`,
        address: a,
      })),
    [addresses],
  )

  const handleChange = (next: string | null) => {
    onChange?.(next)
    onPick?.(next ? (addresses.find((a) => a.id === next) ?? null) : null)
  }

  return (
    <>
      <Select<string, AddressSelectOption>
        style={{ width: '100%', ...style }}
        value={value ?? undefined}
        onChange={handleChange}
        options={options}
        loading={loading}
        disabled={disabled}
        allowClear
        showSearch
        optionFilterProp="label"
        placeholder={t('address.select_placeholder')}
        popupMatchSelectWidth={false}
        dropdownStyle={{ minWidth: 420 }}
        optionRender={(option) => (
          <AddressOptionRow address={option.data.address} sharedLabel={t('address.shared_badge')} />
        )}
        dropdownRender={(menu) => (
          <>
            {menu}
            <Divider style={{ margin: '4px 0' }} />
            <Button
              type="text"
              icon={<PlusOutlined />}
              block
              // Keep the dropdown open on click so the modal opens over it.
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => setModalOpen(true)}
            >
              {t('address.create_action')}
            </Button>
          </>
        )}
        notFoundContent={
          loading ? undefined : (
            <Typography.Text type="secondary">{t('address.empty')}</Typography.Text>
          )
        }
      />
      <DeliveryAddressModal
        open={modalOpen}
        canMaintainShared={canMaintainShared}
        onCancel={() => setModalOpen(false)}
        onSaved={(saved) => {
          setModalOpen(false)
          void reload()
          // Select the new entry immediately: creating it was the intent.
          onChange?.(saved.id)
          onPick?.(saved)
        }}
      />
    </>
  )
}
