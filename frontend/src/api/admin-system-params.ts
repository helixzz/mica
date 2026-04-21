import { client } from './client';

export interface SystemParameter {
  id: string;
  key: string;
  category: string;
  value: any;
  data_type: 'int' | 'float' | 'bool' | 'string' | 'decimal';
  default_value: any;
  min_value: number | null;
  max_value: number | null;
  unit: string | null;
  description_zh: string;
  description_en: string;
  is_sensitive: boolean;
  updated_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export async function listSystemParams(): Promise<SystemParameter[]> {
  const response = await client.get('/api/v1/admin/system-params');
  return response.data;
}

export async function getSystemParam(key: string): Promise<SystemParameter> {
  const response = await client.get(`/api/v1/admin/system-params/${key}`);
  return response.data;
}

export async function updateSystemParam(key: string, value: unknown): Promise<SystemParameter> {
  const response = await client.put(`/api/v1/admin/system-params/${key}`, { value });
  return response.data;
}

export async function resetSystemParam(key: string): Promise<SystemParameter> {
  const response = await client.post(`/api/v1/admin/system-params/${key}/reset`);
  return response.data;
}
