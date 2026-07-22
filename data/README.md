# Knowledge base PDFs

Active corpus (indexed by `create_memory_for_llm.py`):

| File | Role |
|------|------|
| `The_GALE_ENCYCLOPEDIA_of_MEDICINE_SECOND.pdf` | Broad medical encyclopedia (original) |
| `Medically_Eczema_and_Itchy_Rash_Guide.pdf` | Skin / itch / dermatitis educational guide |
| `Medically_Diabetes_Overview.pdf` | Diabetes overview |
| `Medically_Hypertension_Overview.pdf` | Hypertension overview |
| `Medically_Allergic_Reactions_and_Anaphylaxis.pdf` | Allergy / anaphylaxis primer |
| `OpenStax_Integumentary_System_Skin.pdf` | OpenStax CC BY extract (skin / integumentary) |
| `WHO_Aids_Headache_Disorders_Primary_Care.pdf` | WHO/EHF headache primary-care aids |

`_archive/` holds the full OpenStax Anatomy & Physiology PDF (too large for routine ingest).

Regenerate topic guides / OpenStax extract:

```bash
python scripts/build_kb_pdfs.py
python create_memory_for_llm.py
```
