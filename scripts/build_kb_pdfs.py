"""Build 5 focused open-licensed PDFs for the Medically knowledge base."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

DATA = Path(__file__).resolve().parent.parent / "data"
OPENSTAX = DATA / "OpenStax_Anatomy_and_Physiology.pdf"
OPENSTAX_ARCHIVE = DATA / "_archive" / "OpenStax_Anatomy_and_Physiology.pdf"


class DocPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(90, 90, 90)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def ascii_safe(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def write_text_pdf(path: Path, title: str, sections: list[tuple[str, str]], source_note: str):
    pdf = DocPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 8, ascii_safe(title))
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, ascii_safe(source_note))
    pdf.ln(4)

    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, ascii_safe(heading))
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, ascii_safe(body))
        pdf.ln(3)

    pdf.output(str(path))
    print(f"Wrote {path.name} ({path.stat().st_size} bytes)")


def extract_openstax_by_keywords(out_name: str, keywords: list[str], max_pages: int = 35) -> Path | None:
    source = OPENSTAX if OPENSTAX.exists() else OPENSTAX_ARCHIVE
    if not source.exists():
        print("OpenStax PDF missing; skip extract", out_name)
        return None

    reader = PdfReader(str(source))
    hits: list[int] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").lower()
        if any(k.lower() in text for k in keywords):
            hits.append(i)
        if len(hits) >= max_pages:
            break

    if not hits:
        print(f"No pages matched for {out_name}")
        return None

    # Expand hits into contiguous-ish ranges around matches
    selected = set()
    for h in hits[: max_pages // 2 + 1]:
        for p in range(max(0, h - 1), min(len(reader.pages), h + 2)):
            selected.add(p)
    pages = sorted(selected)[:max_pages]

    writer = PdfWriter()
    for p in pages:
        writer.add_page(reader.pages[p])
    out = DATA / out_name
    with out.open("wb") as f:
        writer.write(f)
    print(f"Extracted {out.name}: {len(pages)} pages")
    return out


def main():
    DATA.mkdir(exist_ok=True)

    # 1) Dermatitis / itchy rash educational brief
    write_text_pdf(
        DATA / "Medically_Eczema_and_Itchy_Rash_Guide.pdf",
        "Eczema, Dermatitis, and Itchy Red Skin Marks — Educational Guide",
        [
            (
                "Overview",
                "Itchy red marks on the skin are common and have many possible causes. "
                "Frequent explanations include eczema (atopic dermatitis), contact dermatitis, "
                "urticaria (hives), fungal infections, insect bites, and allergic reactions. "
                "This guide summarizes educational information for retrieval-augmented assistants "
                "and is not a diagnosis.",
            ),
            (
                "Eczema (Atopic Dermatitis)",
                "Eczema often causes dry, itchy, inflamed skin that may look red or darker than "
                "surrounding skin depending on complexion. Scratching can worsen irritation and "
                "lead to thickened skin or secondary infection. Triggers may include soaps, "
                "fragrances, sweat, allergens, stress, and climate changes. Supportive care usually "
                "emphasizes gentle cleansing, frequent moisturizing, avoiding known irritants, and "
                "seeking medical care for severe, spreading, or infected rashes.",
            ),
            (
                "Contact Dermatitis",
                "Contact dermatitis appears after the skin touches an irritant or allergen such as "
                "nickel, poison ivy, latex, cosmetics, or cleaning chemicals. The rash is often "
                "localized to the exposure area and may burn, itch, or blister. Identifying and "
                "removing the trigger is central. Persistent or severe reactions warrant clinician "
                "evaluation.",
            ),
            (
                "Urticaria (Hives) and Allergy Clues",
                "Hives are raised, itchy welts that can appear suddenly and migrate. They may follow "
                "foods, medicines, infections, or unknown triggers. Immediate medical attention is "
                "needed for swelling of lips/tongue/throat, breathing difficulty, dizziness, or "
                "fainting, which can signal anaphylaxis.",
            ),
            (
                "When to Seek Care",
                "Seek urgent care for rapidly spreading rash with fever, pain, pus, blistering over "
                "large areas, facial/oral swelling, or breathing problems. For chronic itch with red "
                "marks, a clinician can help distinguish eczema from infection, psoriasis, scabies, "
                "or other conditions.",
            ),
        ],
        "Compiled for Medically RAG demo from common public-health educational themes "
        "(educational use only; not clinical advice).",
    )

    # 2) Diabetes educational brief
    write_text_pdf(
        DATA / "Medically_Diabetes_Overview.pdf",
        "Diabetes Mellitus — Educational Overview",
        [
            (
                "What is diabetes?",
                "Diabetes mellitus is a chronic condition marked by high blood glucose. It occurs "
                "when the body does not make enough insulin (commonly type 1) or cannot use insulin "
                "effectively (commonly type 2). Gestational diabetes can appear during pregnancy. "
                "Uncontrolled high glucose over time can damage vessels, nerves, kidneys, eyes, and "
                "the heart.",
            ),
            (
                "Common symptoms",
                "Symptoms can include increased thirst, frequent urination, unexplained weight "
                "change, fatigue, blurred vision, slow-healing sores, and recurrent infections. "
                "Some people with type 2 diabetes have few early symptoms, so screening matters for "
                "at-risk adults.",
            ),
            (
                "Risk factors and prevention focus",
                "Type 2 risk rises with overweight/obesity, physical inactivity, older age, family "
                "history, and certain cardiometabolic conditions. Helpful prevention themes include "
                "balanced diet, activity, healthy weight, tobacco avoidance, and regular checkups. "
                "Type 1 is autoimmune and not prevented by lifestyle alone.",
            ),
            (
                "Management themes",
                "Management may combine glucose monitoring, nutrition, physical activity, medicines "
                "(including insulin when needed), blood-pressure and cholesterol care, foot checks, "
                "and eye exams. Individual plans must come from qualified clinicians.",
            ),
        ],
        "Educational summary aligned with widely published WHO/public-health diabetes themes "
        "(not a substitute for WHO documents or medical care).",
    )

    # 3) Hypertension educational brief
    write_text_pdf(
        DATA / "Medically_Hypertension_Overview.pdf",
        "Hypertension (High Blood Pressure) — Educational Overview",
        [
            (
                "Definition",
                "Hypertension is sustained high blood pressure. It is often called a silent "
                "condition because many people feel well until complications appear. Long-term "
                "hypertension increases risk of heart attack, stroke, kidney disease, and other "
                "vascular problems.",
            ),
            (
                "Contributing factors",
                "Contributors can include excess salt intake, unhealthy diet, physical inactivity, "
                "obesity, tobacco and heavy alcohol use, stress, aging, family history, kidney "
                "disease, and some medicines. Air pollution and other environmental factors are "
                "also discussed in public-health literature.",
            ),
            (
                "Measurement and goals",
                "Blood pressure is typically recorded as systolic/diastolic values. Diagnosis and "
                "targets depend on clinical guidelines and personal risk (for example coexisting "
                "diabetes or kidney disease). Home monitoring can complement clinic readings when "
                "advised by a clinician.",
            ),
            (
                "Lifestyle and treatment themes",
                "Common non-drug themes include reducing salt, eating more vegetables/fruits, "
                "maintaining activity, limiting alcohol, stopping tobacco, and managing weight. "
                "Medicines are often required and must be prescribed and adjusted by clinicians. "
                "Suddenly stopping medicines without advice can be unsafe.",
            ),
        ],
        "Educational summary aligned with common WHO hypertension public-health themes "
        "(educational use only).",
    )

    # 4) Allergic reactions / first response themes
    write_text_pdf(
        DATA / "Medically_Allergic_Reactions_and_Anaphylaxis.pdf",
        "Allergic Reactions and Anaphylaxis — Educational Primer",
        [
            (
                "Spectrum of allergic reactions",
                "Allergies occur when the immune system reacts to normally harmless substances. "
                "Symptoms range from mild (sneezing, itchy eyes, hives) to severe systemic "
                "reactions. Seasonal allergy, food allergy, drug allergy, and eczema-related "
                "itch are common presentations in educational materials.",
            ),
            (
                "Skin signs",
                "Skin findings may include itchy red patches, raised welts (urticaria), swelling "
                "(angioedema), or eczematous rash. New widespread rash after a medicine or food "
                "exposure should be discussed with a clinician, especially if accompanied by "
                "breathing or swallowing difficulty.",
            ),
            (
                "Anaphylaxis warning signs",
                "Emergency features can include trouble breathing, wheezing, throat tightness, "
                "swollen tongue/lips, repeated vomiting, dizziness, collapse, or a sense of "
                "impending doom. This is a medical emergency requiring immediate emergency "
                "services. People prescribed epinephrine auto-injectors should follow their "
                "clinician's emergency plan.",
            ),
            (
                "Practical educational points",
                "Avoid known triggers when identified, read labels for food allergies, and keep "
                "emergency medicines accessible if prescribed. Antihistamines may help some mild "
                "symptoms but do not replace emergency care for anaphylaxis.",
            ),
        ],
        "Educational primer for Medically RAG; not emergency protocol or clinical advice.",
    )

    # 5) Extract OpenStax integumentary-focused pages (CC BY)
    extract_openstax_by_keywords(
        "OpenStax_Integumentary_System_Skin.pdf",
        keywords=[
            "integumentary system",
            "epidermis",
            "dermis",
            "sweat gland",
            "hair follicle",
        ],
        max_pages=40,
    )

    # Keep ingest practical: archive the huge full OpenStax book after chapter extract.
    if OPENSTAX.exists():
        archive = DATA / "_archive"
        archive.mkdir(exist_ok=True)
        target = archive / OPENSTAX.name
        if target.exists():
            OPENSTAX.unlink()
            print("Removed duplicate full OpenStax from data/")
        else:
            OPENSTAX.replace(target)
            print(f"Moved full OpenStax book to {target}")

    print("\nPDF inventory (active knowledge base):")
    for p in sorted(DATA.glob("*.pdf")):
        print(f" - {p.name} ({p.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
