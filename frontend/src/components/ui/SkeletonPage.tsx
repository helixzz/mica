import React from 'react';
import { Skeleton, Card, Row, Col, Space } from 'antd';

interface SkeletonPageProps {
  rows?: number;
}

export const SkeletonPage: React.FC<SkeletonPageProps> = ({ rows = 3 }) => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Skeleton active paragraph={{ rows: 1 }} />
      <Row gutter={[16, 16]}>
        {[1, 2, 3].map((i) => (
          <Col xs={24} sm={8} key={i}>
            <Card>
              <Skeleton active paragraph={{ rows: 2 }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card>
        <Skeleton active paragraph={{ rows: rows }} />
      </Card>
    </Space>
  );
};
