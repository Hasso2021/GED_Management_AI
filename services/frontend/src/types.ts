export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'analyzed'
  | 'validated'
  | 'rejected'
  | 'failed';

export interface ProposedMetadata {
  title: string;
  organisation: string;
  date: string;
  invoiceNumber: string;
  amount: string;
  siret: string;
  keywords: string;
}

export interface MetadataField {
  value?: string | null;
  source?: string;
  status?: string;
  confidence?: number;
  validated?: boolean;
  original_value?: string | null;
}

export interface DetectedItem {
  key: string;
  label: string;
  value: string;
  source: string;
}

export interface DetectedInformation {
  business: DetectedItem[];
  personal: DetectedItem[];
  containsPotentialPersonalData: boolean;
  categories: string[];
  entities: { type: string; value: string; source: string }[];
}

export interface PiiInfo {
  present: boolean;
  categories: string[];
  entities?: { type: string; value: string; source: string }[];
}

export interface DocumentRecord {
  id: string;
  filename: string;
  mimeType: string;
  fileSize: number;
  status: DocumentStatus;
  documentType: string | null;
  documentTypeLabel: string | null;
  documentTypeSource?: string | null;
  suggestedDocumentType?: string | null;
  suggestedDocumentTypeLabel?: string | null;
  confidence: number | null;
  classificationMethod: string | null;
  ocrText: string | null;
  metadata: ProposedMetadata;
  metadataFields?: Partial<Record<string, MetadataField>>;
  extractedFields: Record<string, unknown>;
  detectedInformation?: DetectedInformation;
  pii: PiiInfo;
  aiInformation?: {
    aiGenerated: boolean;
    validationStatus: string;
  };
  error: string | null;
  nuxeo?: {
    success?: boolean;
    document_id?: string;
    message?: string;
  } | null;
  createdAt: string;
  updatedAt: string;
}

export const METADATA_FIELDS: { key: keyof ProposedMetadata; label: string }[] = [
  { key: 'title', label: 'Titre' },
  { key: 'organisation', label: 'Organisation' },
  { key: 'date', label: 'Date' },
  { key: 'invoiceNumber', label: 'Numéro de facture' },
  { key: 'amount', label: 'Montant' },
  { key: 'siret', label: 'SIRET' },
  { key: 'keywords', label: 'Mots-clés' },
];

export const SOURCE_LABELS: Record<string, string> = {
  regex: 'regex',
  spacy_ner: 'spaCy NER',
  ml_classifier: 'classifieur ML',
  filename: 'nom de fichier',
  deterministic_rule: 'règle déterministe',
  derived_metadata: 'métadonnée dérivée',
  ocr: 'OCR',
  human_modified: 'modifié',
};
