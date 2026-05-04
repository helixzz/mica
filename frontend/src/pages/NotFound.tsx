import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export const NotFound: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <Result
      status="404"
      title={t('error.not_found_title', '404')}
      subTitle={t('error.not_found_desc', 'Sorry, the page you visited does not exist.')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('error.go_dashboard', 'Back Home')}
        </Button>
      }
    />
  );
};
