# Architecture — prototype de thèse

## Décision : une API, une interface, pas d’authentification

Le prototype démontre le pipeline d’enrichissement de métadonnées et pas un système d’information d’entreprise.


- OCR Tesseract (`ocr_engine`, `preprocessor`)
- Classification par mots-clés et modèle ML optionnel
- Extraction regex + spaCy (`extractor`, `regex_patterns`)
- Détection indicative de données personnelles
- Revue humaine (modifier / valider / rejeter) et export JSON


## Stockage

Les fichiers uploadés et l’index JSON vivent dans le volume Docker `demo_data`. Suffisant pour une soutenance.

## Nuxeo

Export Dublin Core compatible uniquement (`dc:title`, `dc:description`, `dc:source`) vers un document existant, après validation humaine. `file:content`, permissions et cycle de vie ne sont pas modifiés. `dc:nature` et `dc:subjects` ne sont pas envoyés (vocabulaires Nuxeo, pas du texte libre).
