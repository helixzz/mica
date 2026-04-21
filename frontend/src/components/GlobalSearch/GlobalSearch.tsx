import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Input, Dropdown, MenuProps, Tag, Typography, Spin, Empty, Button, Modal } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { searchAll, SearchResponse, SearchHit } from '@/api/search';

const { Text } = Typography;

const TYPE_COLORS: Record<string, string> = {
  pr: 'blue',
  po: 'cyan',
  contract: 'purple',
  contract_doc: 'magenta',
  invoice: 'orange',
  supplier: 'green',
  item: 'gold',
};

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

export const GlobalSearch: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const inputRef = useRef<any>(null);
  const [isMobileModalOpen, setIsMobileModalOpen] = useState(false);

  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (e.key === 'Escape') {
        setOpen(false);
        setQuery('');
        inputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (debouncedQuery.length >= 2) {
      setLoading(true);
      searchAll(debouncedQuery, { limit: 5 })
        .then(res => {
          setResults(res);
          setOpen(true);
        })
        .catch(err => console.error('Search error:', err))
        .finally(() => setLoading(false));
    } else {
      setResults(null);
      setOpen(false);
    }
  }, [debouncedQuery]);

  const handleSelect = (url: string) => {
    setOpen(false);
    setQuery('');
    setIsMobileModalOpen(false);
    navigate(url);
  };

  const handleSeeAll = () => {
    setOpen(false);
    setIsMobileModalOpen(false);
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  const items: MenuProps['items'] = useMemo(() => {
    if (loading) {
      return [{ key: 'loading', label: <div style={{ padding: 16, textAlign: 'center' }}><Spin /></div> }];
    }
    if (!results || results.total === 0) {
      return [{ key: 'empty', label: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('search.noResults', { query })} /> }];
    }

    const menuItems: MenuProps['items'] = [];
    
    Object.entries(results.by_type).forEach(([type, hits]) => {
      if (hits.length === 0) return;
      
      menuItems.push({
        type: 'group',
        label: t(`search.types.${type}`, type.toUpperCase()),
        children: hits.map(hit => ({
          key: hit.entity_id,
          label: (
            <div onClick={() => handleSelect(hit.link_url)} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong ellipsis style={{ maxWidth: 200 }}>{hit.title}</Text>
                <Tag color={TYPE_COLORS[type] || 'default'}>{t(`search.types.${type}`, type)}</Tag>
              </div>
              {hit.snippet && <Text type="secondary" ellipsis style={{ fontSize: 12 }}>{hit.snippet}</Text>}
            </div>
          ),
        })),
      });
    });

    menuItems.push({ type: 'divider' });
    menuItems.push({
      key: 'see-all',
      label: (
        <div onClick={handleSeeAll} style={{ textAlign: 'center', color: '#1890ff' }}>
          {t('search.seeAll', { count: results.total })}
        </div>
      ),
    });

    return menuItems;
  }, [results, loading, t, query]);

  const searchInput = (
    <Dropdown
      menu={{ items }}
      open={open && query.length >= 2}
      onOpenChange={setOpen}
      trigger={['click']}
      overlayStyle={{ width: 400, maxHeight: 500, overflowY: 'auto' }}
    >
      <Input
        ref={inputRef}
        placeholder={t('search.placeholder')}
        prefix={<SearchOutlined />}
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => query.length >= 2 && setOpen(true)}
        style={{ width: 300 }}
        allowClear
        suffix={<Text type="secondary" style={{ fontSize: 12 }}>⌘K</Text>}
      />
    </Dropdown>
  );

  return (
    <>
      <div className="hidden md:block">
        {searchInput}
      </div>
      <div className="md:hidden">
        <Button type="text" icon={<SearchOutlined />} onClick={() => setIsMobileModalOpen(true)} />
        <Modal
          open={isMobileModalOpen}
          onCancel={() => setIsMobileModalOpen(false)}
          footer={null}
          closable={false}
          style={{ top: 20 }}
          bodyStyle={{ padding: 0 }}
        >
          <div style={{ padding: 16 }}>
            <Input
              autoFocus
              placeholder={t('search.placeholder')}
              prefix={<SearchOutlined />}
              value={query}
              onChange={e => setQuery(e.target.value)}
              allowClear
              size="large"
            />
          </div>
          <div style={{ maxHeight: 'calc(100vh - 150px)', overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: 32, textAlign: 'center' }}><Spin /></div>
            ) : results && results.total > 0 ? (
              <div style={{ padding: '0 16px 16px' }}>
                {Object.entries(results.by_type).map(([type, hits]) => {
                  if (hits.length === 0) return null;
                  return (
                    <div key={type} style={{ marginBottom: 16 }}>
                      <div style={{ marginBottom: 8, fontWeight: 'bold', color: '#8c8c8c' }}>
                        {t(`search.types.${type}`, type.toUpperCase())}
                      </div>
                      {hits.map(hit => (
                        <div
                          key={hit.entity_id}
                          onClick={() => handleSelect(hit.link_url)}
                          style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Text strong>{hit.title}</Text>
                            <Tag color={TYPE_COLORS[type] || 'default'}>{t(`search.types.${type}`, type)}</Tag>
                          </div>
                          {hit.snippet && <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>{hit.snippet}</Text>}
                        </div>
                      ))}
                    </div>
                  );
                })}
                <Button type="link" block onClick={handleSeeAll}>
                  {t('search.seeAll', { count: results.total })}
                </Button>
              </div>
            ) : query.length >= 2 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('search.noResults', { query })} />
            ) : null}
          </div>
        </Modal>
      </div>
    </>
  );
};
