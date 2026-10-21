import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export interface SeedManifest {
  po_id: string;
  po_number: string;
  contract_id: string | null;
  contract_number: string | null;
  contract_currency: string | null;
  rfq_id: string | null;
  rfq_number: string | null;
}

/**
 * Identifiers written by ../seed_data.py.
 *
 * Specs used to pin a number like "PO-2026-0005", which changes the moment the seed
 * runs against a fresh database. Reading what the seed actually created keeps them
 * honest; returning null lets a spec skip rather than fail.
 *
 * Resolved from the working directory because Playwright compiles these specs to
 * CommonJS, where import.meta is not available.
 */
export function readSeedManifest(): SeedManifest | null {
  try {
    return JSON.parse(readFileSync(resolve(process.cwd(), '.seed.json'), 'utf8')) as SeedManifest;
  } catch {
    return null;
  }
}
