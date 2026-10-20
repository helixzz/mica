import { Badge, Button, Drawer, Space, Tag, Typography } from 'antd'
import { GiftOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { RELEASES, type ReleaseKind } from './releases'

const SEEN_KEY = 'mica.whatsnew.seen'

const KIND_COLOR: Record<ReleaseKind, string> = {
  new: 'success',
  fix: 'warning',
  improvement: 'processing',
}

/**
 * Release history in a drawer, opened from the header.
 *
 * The header button carries a dot until the latest version has been looked at,
 * so improvements are noticed without anyone sending an email about them.
 */
export function WhatsNewButton() {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const [seen, setSeen] = useState<string | null>(null)

  useEffect(() => {
    setSeen(localStorage.getItem(SEEN_KEY))
  }, [])

  const latest = RELEASES[0]?.version
  const unread = !!latest && seen !== latest
  const isZh = i18n.language.startsWith('zh')

  const openDrawer = () => {
    setOpen(true)
    if (latest) {
      localStorage.setItem(SEEN_KEY, latest)
      setSeen(latest)
    }
  }

  return (
    <>
      <Badge dot={unread} offset={[-4, 4]}>
        <Button
          type="text"
          onClick={openDrawer}
          title={t('whats_new.tooltip')}
          aria-label={t('whats_new.tooltip')}
          icon={<GiftOutlined />}
          className="no-print"
        />
      </Badge>

      <Drawer
        title={t('whats_new.title')}
        placement="right"
        width={520}
        open={open}
        onClose={() => setOpen(false)}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {RELEASES.map((release) => (
            <div key={release.version}>
              <Space align="center" style={{ marginBottom: 8 }}>
                <Typography.Text strong>v{release.version}</Typography.Text>
                <Typography.Text type="secondary">{release.date}</Typography.Text>
              </Space>
              <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }}>
                {release.items.map((item, index) => (
                  <li
                    key={`${release.version}-${index}`}
                    style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}
                  >
                    <Tag color={KIND_COLOR[item.kind]} style={{ marginInlineEnd: 0, flexShrink: 0 }}>
                      {t(`whats_new.kind_${item.kind}`)}
                    </Tag>
                    <Typography.Text>{isZh ? item.zh : item.en}</Typography.Text>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Space>
      </Drawer>
    </>
  )
}
