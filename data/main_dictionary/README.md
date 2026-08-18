# Main Melimi Dictionary

The main Melimi lexical source is tracked as a provenance-aware authority layer.
The current source manifest is **Bangaaru Naanelu — A Dictionary of Pure Telugu**
by **Vaachaspathy (2021)**, as designated by the project owner.

## Authority pipeline

```text
source PDF
   ↓
extraction / OCR
   ↓
NORMALIZED
   ↓
human/source verification
   ↓
APPROVED
   ↓
main_dictionary importer
   ↓
MASTER MelimiRoot + provenance metadata
   ↓
root-first morphology / retrieval / validation
```

Raw PDF or OCR output must never be imported directly into MASTER.

## Reviewed entry format

```json
{
  "standard_form": "...",
  "melimi_form": "...",
  "meaning": "...",
  "part_of_speech": "noun",
  "grammatical_category": "...",
  "root": "...",
  "derived_forms": [],
  "variants": [],
  "domain": "",
  "examples": [],
  "notes": "",
  "source_page": 123,
  "source_entry": "...",
  "confidence": "SOURCE_CONFIRMED",
  "status": "APPROVED"
}
```

`NEEDS_REVIEW`, `PENDING`, malformed, or provenance-free entries are rejected
by the importer.

## Runtime authority

Main-dictionary roots are stored with the protected source identifier:

`main_dictionary:bangaaru_naanelu:2021`

A direct `/word` registration cannot overwrite such a root. Changes to the
main dictionary must go through the reviewed source/import pipeline.

## Important separation

- **Dictionary:** establishes which lexical mappings are authoritative.
- **Morphology:** generates inflected/derived forms from the authoritative root.
- **Grammar:** determines how forms function in sentences.
- **Knowledge:** stores explanations, examples, and other language knowledge.
- **LLM:** reasons over retrieved evidence and generates responses.
- **Validator:** prevents unsupported Melimi claims.

The repository intentionally does **not** contain a blind 498-page PDF-to-MASTER
import. The source must first be extracted and reviewed against the actual pages.
