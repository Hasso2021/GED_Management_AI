import axios from 'axios';
import type { DocumentRecord, ProposedMetadata } from './types';

const api = axios.create({
  baseURL: '/api',
  timeout: 300_000,
});

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<DocumentRecord>('/documents', form);
  return data;
}

export async function analyzeDocument(id: string): Promise<DocumentRecord> {
  const { data } = await api.post<DocumentRecord>(`/documents/${id}/analyze`);
  return data;
}

export async function getDocument(id: string): Promise<DocumentRecord> {
  const { data } = await api.get<DocumentRecord>(`/documents/${id}`);
  return data;
}

export async function patchMetadata(
  id: string,
  metadata: ProposedMetadata,
): Promise<DocumentRecord> {
  const { data } = await api.patch<DocumentRecord>(`/documents/${id}/metadata`, metadata);
  return data;
}

export async function validateDocument(id: string): Promise<DocumentRecord> {
  const { data } = await api.post<DocumentRecord>(`/documents/${id}/validate`);
  return data;
}

export async function rejectDocument(id: string): Promise<DocumentRecord> {
  const { data } = await api.post<DocumentRecord>(`/documents/${id}/reject`);
  return data;
}

export async function fetchExportJson(id: string): Promise<Record<string, unknown>> {
  const { data } = await api.get<Record<string, unknown>>(`/documents/${id}/json`);
  return data;
}

export interface NuxeoSendResult {
  success: boolean;
  document_id?: string;
  message: string;
}

export async function sendToNuxeo(
  id: string,
  nuxeoDocumentId: string,
): Promise<NuxeoSendResult> {
  const { data } = await api.post<NuxeoSendResult>(`/documents/${id}/nuxeo`, {
    nuxeoDocumentId,
  });
  return data;
}
