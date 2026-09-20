#!/usr/bin/env bash
# generate_dataset.sh — Generate the full DocFlow synthetic dataset
# Usage: ./generate_dataset.sh [output_dir]

set -euo pipefail

OUTPUT_DIR="${1:-./samples}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> DocFlow dataset generation started"
echo "    Output: ${OUTPUT_DIR}"

# Ensure Python deps
if ! python3 -c "import pathlib" 2>/dev/null; then
  echo "ERROR: Python 3 is required" >&2
  exit 1
fi

# 1. Invoices (50 FACTURE + 20 DEVIS)
echo "--> Generating invoices..."
python3 "${SCRIPT_DIR}/generate_invoices.py" \
  --count 50 --type FACTURE --output "${OUTPUT_DIR}/invoices"

python3 "${SCRIPT_DIR}/generate_invoices.py" \
  --count 20 --type DEVIS --output "${OUTPUT_DIR}/devis"

# 2. SIRET attestations + KBIS
echo "--> Generating SIRET/KBIS documents..."
python3 "${SCRIPT_DIR}/generate_siret.py" \
  --count 20 --type SIRET_ATTESTATION --output "${OUTPUT_DIR}/siret"

python3 "${SCRIPT_DIR}/generate_siret.py" \
  --count 20 --type KBIS --output "${OUTPUT_DIR}/kbis"

# 3. Noisy variants for robustness testing
echo "--> Generating noisy variants..."
python3 "${SCRIPT_DIR}/generate_noise.py" \
  --input "${OUTPUT_DIR}/invoices" \
  --output "${OUTPUT_DIR}/noisy_invoices" \
  --noise 0.05

python3 "${SCRIPT_DIR}/generate_noise.py" \
  --input "${OUTPUT_DIR}/invoices" \
  --output "${OUTPUT_DIR}/very_noisy_invoices" \
  --noise 0.15

# 4. Summary
echo ""
echo "==> Dataset generation complete!"
echo ""
find "${OUTPUT_DIR}" -name "*.txt" | wc -l | xargs -I{} echo "    Total files: {}"
echo ""
for dir in invoices devis siret kbis noisy_invoices very_noisy_invoices; do
  count=$(find "${OUTPUT_DIR}/${dir}" -name "*.txt" 2>/dev/null | wc -l)
  printf "    %-25s %d files\n" "${dir}" "${count}"
done
