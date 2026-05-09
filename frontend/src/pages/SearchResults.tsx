import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Typography, Tabs, List, Tag, Spin, Empty, Card } from 'antd';
import { useTranslation } from 'react-i18next';
import { searchAll, SearchResponse, SearchHit } from '@/api/search';

const { Title, Text } = Typography;

const LAST_SEARCH_KEY = 'mica.last_search';

function highlightMarks(snippet: string): React.ReactNode {
  const parts = snippet.split(/(<mark>.*?<\/mark>)/g)
  return parts.map((part, i) => {
    if (part.startsWith('<mark>') && part.endsWith('</mark>')) {
      return <mark key={i}>{part.slice(6, -7)}</mark>
    }
    return part
  })
}

const TYPE_COLORS: Record<string, string> = {
  pr: 'blue',
  po: 'cyan',
  contract: 'purple',
  contract_doc: 'magenta',
  invoice: 'orange',
  supplier: 'green',
  item: 'gold',
};

const TAB_TYPES = ['pr', 'po', 'contract', 'invoice', 'supplier', 'item'] as const;

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
      localStorage.setItem(LAST_SEARCH_KEY, query);
      searchAll(query, { limit: 50 })
        .then(res => {
          setResults(res);
          if (activeTab !== 'all' && getTabCount(res, activeTab) === 0) {
            setActiveTab('all');
          }
        })
        .catch(err => console.error('Search error:', err))
        .finally(() => setLoading(false));
    } else {
      setResults(null);
      const saved = localStorage.getItem(LAST_SEARCH_KEY);
      if (saved) {
        navigate(`/search?q=${encodeURIComponent(saved)}`, { replace: true });
      }
    }
  }, [query, navigate]);

  const getTypeHits = (type: string): SearchHit[] => {
    if (!results) return [];
    if (type === 'contract') {
      return [
        ...(results.by_type['contract'] || []),
        ...(results.by_type['contract_doc'] || []),
      ];
    }
    return results.by_type[type] || [];
  };

  const getTabCount = (res: SearchResponse, type: string): number => {
    if (type === 'contract') {
      return (res.by_type['contract']?.length || 0) + (res.by_type['contract_doc']?.length || 0);
    }
    return res.by_type[type]?.length || 0;
  };

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
                <span>{highlightMarks(hit.snippet)}</span>
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
    ...TAB_TYPES.map(type => {
      const count = results ? getTabCount(results, type) : 0;
      return {
        key: type,
        label: `${t(`search.types.${type}`, type.toUpperCase())} (${count})`,
        disabled: count === 0,
        children: (
          <List
            loading={loading}
            dataSource={getTypeHits(type)}
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
