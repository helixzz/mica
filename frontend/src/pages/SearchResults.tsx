import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Typography, Tabs, List, Tag, Spin, Empty, Card } from 'antd';
import { useTranslation } from 'react-i18next';
import { searchAll, SearchResponse, SearchHit } from '@/api/search';

const { Title, Text } = Typography;

const TYPE_COLORS: Record<string, string> = {
  pr: 'blue',
  po: 'cyan',
  contract: 'purple',
  contract_doc: 'magenta',
  invoice: 'orange',
  supplier: 'green',
  item: 'gold',
};

export const SearchResults: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<string>('all');

  useEffect(() => {
    if (query) {
      setLoading(true);
      searchAll(query, { limit: 50 })
        .then(res => {
          setResults(res);
          if (activeTab !== 'all' && (!res.by_type[activeTab] || res.by_type[activeTab].length === 0)) {
            setActiveTab('all');
          }
        })
        .catch(err => console.error('Search error:', err))
        .finally(() => setLoading(false));
    } else {
      setResults(null);
    }
  }, [query]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };

  const renderHit = (hit: SearchHit) => (
    <List.Item
      key={hit.entity_id}
      onClick={() => navigate(hit.link_url)}
      style={{ cursor: 'pointer', padding: '16px', background: '#fff', marginBottom: '8px', borderRadius: '8px', border: '1px solid #f0f0f0' }}
      className="hover:shadow-md transition-shadow"
    >
      <List.Item.Meta
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Text strong style={{ fontSize: '16px' }}>{hit.title}</Text>
            <Tag color={TYPE_COLORS[hit.entity_type] || 'default'}>
              {t(`search.types.${hit.entity_type}`, hit.entity_type)}
            </Tag>
          </div>
        }
        description={
          <div style={{ marginTop: '8px' }}>
            {hit.snippet && (
              <div style={{ marginBottom: '8px', color: '#595959' }}>
                <span dangerouslySetInnerHTML={{ __html: hit.snippet }} />
              </div>
            )}
            {hit.meta && Object.keys(hit.meta).length > 0 && (
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '12px', color: '#8c8c8c' }}>
                {Object.entries(hit.meta).map(([k, v]) => (
                  <span key={k}>
                    <strong>{t(`search.meta.${k}`, k)}:</strong> {String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>
        }
      />
    </List.Item>
  );

  if (!query) {
    return (
      <div style={{ padding: '24px' }}>
        <Empty description={t('search.enterQuery')} />
      </div>
    );
  }

  const allTypes = ['pr', 'po', 'contract', 'supplier', 'item', 'invoice', 'contract_doc'];
  
  const tabItems = [
    {
      key: 'all',
      label: `${t('search.tabs.all')} (${results?.total || 0})`,
      children: (
        <List
          loading={loading}
          dataSource={results?.top_hits || []}
          renderItem={renderHit}
          locale={{ emptyText: <Empty description={t('search.noResults', { query })} /> }}
        />
      ),
    },
    ...allTypes.map(type => {
      const count = results?.by_type[type]?.length || 0;
      return {
        key: type,
        label: `${t(`search.types.${type}`, type.toUpperCase())} (${count})`,
        disabled: count === 0,
        children: (
          <List
            loading={loading}
            dataSource={results?.by_type[type] || []}
            renderItem={renderHit}
          />
        ),
      };
    })
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2} style={{ marginBottom: '24px' }}>
        {t('search.resultsFor', { query })}
      </Title>
      
      {loading && !results ? (
        <div style={{ textAlign: 'center', padding: '48px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabItems}
          size="large"
        />
      )}
    </div>
  );
};

export default SearchResults;
