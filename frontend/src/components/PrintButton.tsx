import React from 'react';
import { Button } from 'antd';
import { PrinterOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface PrintButtonProps {
  label?: string;
  size?: 'small' | 'middle' | 'large';
}

export const PrintButton: React.FC<PrintButtonProps> = ({ label, size = 'middle' }) => {
  const { t } = useTranslation();
  return (
    <Button
      icon={<PrinterOutlined />}
      size={size}
      className="no-print"
      onClick={() => window.print()}
    >
      {label ?? t('button.print')}
    </Button>
  );
};

export default PrintButton;
