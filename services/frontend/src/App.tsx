import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Loader2, Upload } from 'lucide-react';
import {
  analyzeDocument,
  fetchExportJson,
  patchMetadata,
  rejectDocument,
  sendToNuxeo,
  uploadDocument,
  validateDocument,
} from './api';
import { METADATA_FIELDS, SOURCE_LABELS, type DocumentRecord, type ProposedMetadata } from './types';

const NUXEO_TEST_DOCUMENT_ID = '6d259726-d851-45fb-bd94-672d5ef56c0e';

function formatConfidence(value: number | null): string {
  if (value == null) return '—';
  return `${Math.round(value * 100)} %`;
}

function errorMessage(err: unknown): string {
  if (typeof err === 'object' && err !== null) {
    const axiosErr = err as {
      code?: string;
      message?: string;
      response?: { status?: number; data?: { detail?: string; message?: string } };
    };
    const code = axiosErr.code;
    const status = axiosErr.response?.status;
    if (
      code === 'ERR_NETWORK' ||
      code === 'ECONNREFUSED' ||
      (status === 500 && !axiosErr.response?.data?.detail && !axiosErr.response?.data?.message)
    ) {
      return 'API FastAPI injoignable sur http://127.0.0.1:8000. Démarrez Uvicorn dans le venv.';
    }
    if (axiosErr.response?.data?.message) return axiosErr.response.data.message;
    if (axiosErr.response?.data?.detail) return axiosErr.response.data.detail;
  }
  if (err instanceof Error) return err.message;
  return 'Une erreur est survenue.';
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [draft, setDraft] = useState<ProposedMetadata | null>(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState<
    'upload' | 'analyze' | 'save' | 'validate' | 'reject' | 'nuxeo' | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [nuxeoMessage, setNuxeoMessage] = useState<string | null>(null);
  const [nuxeoOk, setNuxeoOk] = useState(false);
  const [jsonPayload, setJsonPayload] = useState<Record<string, unknown> | null>(null);
  const [showJson, setShowJson] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    const next = accepted[0];
    if (!next) return;
    setFile(next);
    setDoc(null);
    setDraft(null);
    setEditing(false);
    setJsonPayload(null);
    setShowJson(false);
    setError(null);
    setNuxeoMessage(null);
    setNuxeoOk(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tif', '.tiff'],
      'text/plain': ['.txt'],
    },
  });

  const displayedName = file?.name || doc?.filename || '';
  const analyzed = doc?.status === 'analyzed' || doc?.status === 'validated' || doc?.status === 'rejected';
  const nuxeoReady = doc?.status === 'validated';

  const statusLabel = useMemo(() => {
    switch (doc?.status) {
      case 'uploaded':
        return 'Prêt à analyser';
      case 'processing':
        return 'Analyse en cours';
      case 'analyzed':
        return 'Métadonnées proposées';
      case 'validated':
        return 'Validé';
      case 'rejected':
        return 'Rejeté';
      case 'failed':
        return 'Échec';
      default:
        return file ? 'Document sélectionné' : '';
    }
  }, [doc?.status, file]);

  async function handleUploadAndKeep() {
    if (!file) return null;
    setBusy('upload');
    setError(null);
    try {
      const uploaded = await uploadDocument(file);
      setDoc(uploaded);
      return uploaded;
    } catch (err) {
      setError(errorMessage(err));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function handleAnalyze() {
    setError(null);
    let current = doc;
    if (!current) {
      current = await handleUploadAndKeep();
      if (!current) return;
    }
    setBusy('analyze');
    try {
      const analyzedDoc = await analyzeDocument(current.id);
      setDoc(analyzedDoc);
      setDraft(analyzedDoc.metadata);
      setEditing(false);
      setShowJson(false);
      setNuxeoMessage(null);
      setNuxeoOk(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleSaveEdits() {
    if (!doc || !draft) return;
    setBusy('save');
    setError(null);
    try {
      const updated = await patchMetadata(doc.id, draft);
      setDoc(updated);
      setDraft(updated.metadata);
      setEditing(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleValidate() {
    if (!doc) return;
    if (editing && draft) {
      await handleSaveEdits();
    }
    setBusy('validate');
    setError(null);
    try {
      const updated = await validateDocument(doc.id);
      setDoc(updated);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleReject() {
    if (!doc) return;
    setBusy('reject');
    setError(null);
    try {
      const updated = await rejectDocument(doc.id);
      setDoc(updated);
      setShowJson(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleShowJson() {
    if (!doc) return;
    setError(null);
    try {
      const payload = await fetchExportJson(doc.id);
      setJsonPayload(payload);
      setShowJson(true);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleSendNuxeo() {
    if (!doc || doc.status !== 'validated') return;
    setBusy('nuxeo');
    setError(null);
    setNuxeoMessage(null);
    setNuxeoOk(false);
    try {
      const result = await sendToNuxeo(doc.id, NUXEO_TEST_DOCUMENT_ID);
      if (result.success) {
        setNuxeoOk(true);
        setNuxeoMessage(`✓ ${result.message}`);
      } else {
        setNuxeoOk(false);
        setNuxeoMessage(result.message || 'Échec de l’envoi vers Nuxeo.');
      }
    } catch (err) {
      setNuxeoOk(false);
      setNuxeoMessage(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const metadata = draft ?? doc?.metadata;

  return (
    <div className="min-h-screen px-4 py-10 sm:px-8">
      <main className="mx-auto max-w-3xl">
        <header className="mb-10 text-center">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-accent">
            Prototype de thèse
          </p>
          <h1 className="font-serif text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            GED Management AI
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-lg leading-relaxed text-ink/70">
            Enrichissement intelligent des métadonnées documentaires
          </p>
        </header>

        <section className="rounded-2xl border border-line bg-card p-6 shadow-[0_12px_40px_rgba(28,25,21,0.06)]">
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
              isDragActive ? 'border-accent bg-accentsoft' : 'border-line hover:border-accent/60'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto mb-3 h-8 w-8 text-accent" />
            <p className="text-base font-medium">Déposer un document</p>
            <p className="mt-1 text-sm text-ink/55">PDF, image ou fichier texte — un seul fichier</p>
          </div>

          {displayedName && (
            <div className="mt-6 flex items-start gap-3 rounded-lg bg-paper px-4 py-3">
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
              <div>
                <p className="text-xs uppercase tracking-wide text-ink/50">Document</p>
                <p className="font-medium">{displayedName}</p>
                {statusLabel && <p className="mt-1 text-sm text-ink/60">{statusLabel}</p>}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!file && !doc}
            className="mt-6 w-full rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:opacity-40"
          >
            {busy === 'analyze' || busy === 'upload' ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyse en cours…
              </span>
            ) : (
              'Analyser le document'
            )}
          </button>
        </section>

        {error && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </p>
        )}

        {doc?.error && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {doc.error}
          </p>
        )}

        {analyzed && doc && metadata && (
          <>
            <Section title="Document">
              <Field label="Nom du fichier" value={doc.filename} />
              <Field label="Type détecté" value={doc.documentTypeLabel || '—'} />
              <Field label="Confidence" value={formatConfidence(doc.confidence)} />
              {doc.documentType === 'UNKNOWN' && (
                <p className="mt-3 text-sm text-warn">
                  Type hors taxonomie — à classer avant envoi vers Nuxeo.
                  {doc.suggestedDocumentTypeLabel
                    ? ` Hypothèse écartée : ${doc.suggestedDocumentTypeLabel} (${formatConfidence(doc.confidence)}).`
                    : ''}
                </p>
              )}
            </Section>

            <Section title="Métadonnées proposées">
              <div className="space-y-3">
                {METADATA_FIELDS.map(({ key, label }) =>
                  editing ? (
                    <label key={key} className="block">
                      <span className="text-xs uppercase tracking-wide text-ink/50">{label}</span>
                      <input
                        value={metadata[key]}
                        onChange={(e) => setDraft({ ...metadata, [key]: e.target.value })}
                        className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-accent"
                      />
                    </label>
                  ) : (
                    <Field key={key} label={label} value={metadata[key] || '—'} />
                  ),
                )}
              </div>
            </Section>

            <DetectedSection doc={doc} />
            <TechnicalDetails doc={doc} />

            <Section title="Validation">
              <div className="flex flex-wrap gap-3">
                {editing ? (
                  <button
                    type="button"
                    onClick={handleSaveEdits}
                    className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
                  >
                    {busy === 'save' ? 'Enregistrement…' : 'Enregistrer'}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setDraft(doc.metadata);
                      setEditing(true);
                    }}
                    className="rounded-lg border border-line px-4 py-2 text-sm font-semibold"
                  >
                    Modifier
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleValidate}
                  className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
                >
                  {busy === 'validate' ? 'Validation…' : 'Valider'}
                </button>
                <button
                  type="button"
                  onClick={handleReject}
                  className="rounded-lg border border-warn/40 px-4 py-2 text-sm font-semibold text-warn"
                >
                  {busy === 'reject' ? 'Rejet…' : 'Rejeter'}
                </button>
              </div>

              {doc.status === 'validated' && (
                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleShowJson}
                    className="rounded-lg border border-line px-4 py-2 text-sm font-semibold"
                  >
                    Afficher le JSON
                  </button>
                  <button
                    type="button"
                    onClick={handleSendNuxeo}
                    disabled={!nuxeoReady || busy === 'nuxeo'}
                    title={
                      nuxeoReady
                        ? 'Mettre à jour les métadonnées Dublin Core du document Nuxeo existant'
                        : 'Validez d’abord les métadonnées'
                    }
                    className="rounded-lg border border-line px-4 py-2 text-sm font-semibold disabled:opacity-40"
                  >
                    {busy === 'nuxeo' ? 'Envoi vers Nuxeo…' : 'Envoyer vers Nuxeo'}
                  </button>
                </div>
              )}

              {doc.status === 'validated' && (
                <p className="mt-3 text-sm text-accent">Métadonnées validées — prêtes pour l’export.</p>
              )}
              {doc.status === 'validated' && nuxeoMessage && (
                <p className={`mt-2 text-sm ${nuxeoOk ? 'text-accent' : 'text-warn'}`}>{nuxeoMessage}</p>
              )}
              {doc.status === 'rejected' && (
                <p className="mt-3 text-sm text-warn">Proposition rejetée. Vous pouvez relancer une analyse.</p>
              )}
            </Section>

            {showJson && jsonPayload && (
              <Section title="Résultat structuré">
                <pre className="overflow-x-auto rounded-lg bg-ink p-4 font-mono text-xs leading-relaxed text-paper">
                  {JSON.stringify(jsonPayload, null, 2)}
                </pre>
              </Section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function Section({
  title,
  secondary,
  children,
}: {
  title: string;
  secondary?: boolean;
  children: ReactNode;
}) {
  return (
    <section
      className={`mt-6 rounded-2xl border bg-card p-6 ${
        secondary ? 'border-line/70 opacity-95' : 'border-line'
      }`}
    >
      <h2 className="mb-4 font-serif text-xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

function sourceLabel(source?: string | null): string | null {
  if (!source) return null;
  return SOURCE_LABELS[source] || source;
}

function DetectedSection({ doc }: { doc: DocumentRecord }) {
  const info = doc.detectedInformation;
  const business = info?.business ?? [];
  const personal = info?.personal ?? [];
  const present = info?.containsPotentialPersonalData ?? doc.pii.present;

  return (
    <Section title="Informations détectées" secondary>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/50">
        Informations métier
      </h3>
      {business.length ? (
        business.map((item) => (
          <Field key={`${item.key}-${item.value}`} label={item.label} value={item.value} />
        ))
      ) : (
        <p className="mb-3 text-sm text-ink/55">Aucune information métier complémentaire.</p>
      )}

      <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-ink/50">
        Données personnelles potentielles
      </h3>
      {personal.length ? (
        personal.map((item) => (
          <Field key={`${item.key}-${item.value}`} label={item.label} value={item.value} />
        ))
      ) : (
        <p className="mb-3 text-sm text-ink/55">Aucune donnée personnelle potentielle détectée.</p>
      )}

      <Field
        label="Présence potentielle de données personnelles"
        value={present ? 'Oui' : 'Non'}
      />
      <p className="mt-3 text-xs leading-relaxed text-ink/50">
        Détection automatique indicative, à valider. Ce prototype ne constitue pas une analyse de
        conformité RGPD.
      </p>
    </Section>
  );
}

function TechnicalDetails({ doc }: { doc: DocumentRecord }) {
  const rows: { label: string; source: string; extra?: string }[] = [];
  if (doc.documentTypeSource) {
    rows.push({
      label: 'Type de document',
      source: sourceLabel(doc.documentTypeSource) || doc.documentTypeSource,
      extra: doc.confidence != null ? formatConfidence(doc.confidence) : undefined,
    });
  }
  for (const { key, label } of METADATA_FIELDS) {
    const field = doc.metadataFields?.[key];
    if (!field) continue;
    if (!field.source && field.status !== 'not_detected') continue;
    rows.push({
      label,
      source: field.source ? sourceLabel(field.source) || field.source : '—',
      extra: field.status === 'not_detected' ? 'non détecté' : undefined,
    });
  }
  const detected = [
    ...(doc.detectedInformation?.business ?? []),
    ...(doc.detectedInformation?.personal ?? []),
  ];
  for (const item of detected) {
    if (!item.source) continue;
    rows.push({
      label: item.label,
      source: sourceLabel(item.source) || item.source,
    });
  }
  if (!rows.length) return null;

  return (
    <details className="mt-6 rounded-2xl border border-line/70 bg-card">
      <summary className="cursor-pointer px-6 py-3 text-sm text-ink/55 hover:text-ink">
        Détails techniques
      </summary>
      <div className="border-t border-line/70 px-6 py-4">
        {rows.map((row, index) => (
          <div key={`${row.label}-${index}`} className="border-b border-line/70 py-2 last:border-b-0">
            <p className="text-xs uppercase tracking-wide text-ink/50">{row.label}</p>
            <p className="mt-0.5 text-sm text-ink/70">
              {row.source}
              {row.extra ? ` · ${row.extra}` : ''}
            </p>
          </div>
        ))}
      </div>
    </details>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-line/70 py-2 last:border-b-0">
      <p className="text-xs uppercase tracking-wide text-ink/50">{label}</p>
      <p className="mt-0.5 text-[15px]">{value}</p>
    </div>
  );
}
