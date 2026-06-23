import React from 'react';

export interface MonoIdProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const MonoId: React.FC<MonoIdProps> = ({ children, className, style }) => {
  if (children == null || children === '' || children === '-') {
    return <span style={style}>{children ?? '-'}</span>;
  }
  return (
    <code className={['mono-id', className].filter(Boolean).join(' ')} style={style}>
      {children}
    </code>
  );
};

export interface MonoNumProps {
  children: React.ReactNode;
  align?: 'left' | 'right';
  className?: string;
  style?: React.CSSProperties;
}

export const MonoNum: React.FC<MonoNumProps> = ({ children, align, className, style }) => {
  const classes = ['mono-num', align === 'right' ? 'mono-num--right' : null, className]
    .filter(Boolean)
    .join(' ');
  return (
    <span className={classes} style={style}>
      {children}
    </span>
  );
};
