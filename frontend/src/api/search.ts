import { client } from './client';

export interface SearchHit {
  entity_type: string;
  entity_id: string;
  title: string;
  snippet: string | null;
  score: number;
  link_url: string;
  meta: Record<string, unknown>;
}

export interface SearchResponse {
  total: number;
  by_type: Record<string, SearchHit[]>;
  top_hits: SearchHit[];
}

export async function searchAll(query: string, opts?: { types?: string[]; limit?: number }): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.append('q', query);
  if (opts?.types && opts.types.length > 0) {
    params.append('types', opts.types.join(','));
  }
  if (opts?.limit) {
    params.append('limit', opts.limit.toString());
  }
  
  const response = await client.get<SearchResponse>(`/search?${params.toString()}`);
  return response.data;
}
