# FlashDecky — Instant Flash Cards

Make print‑ready flash cards from paste, spreadsheets, or screenshots. Teacher‑friendly. Duplex alignment with fine‑tune offsets. 8 cards per US Letter.

## ✨ Features
- **Inputs**: paste free‑form text, CSV/TSV/XLSX (column mapper), screenshots (PNG/JPG) with optional **OCR.space** extraction.
- **Parsing rules**: numbered/bulleted lists; dictionary style `term (pos.) definition`; separators by **tab**, **colon outside parentheses**, **en/em dash**, or **spaced hyphen**. Wrapped lines append to previous definition. Leading `-` bug fixed.
- **Review & edit**: grid editor (add/delete/bulk paste). Validation flags empty Front/Back. Live card & sheet counts.
- **PDF**: 8 per page, dashed cut lines, **long‑edge mirrored** backs (default) + other duplex modes, **back‑page X/Y offsets (mm)**, optional corner markers, auto-wrap & gentle font auto‑shrink, definition side vertically centered. Footer with `{subject} {unit} {lesson} {page}`.

## 🚀 Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OCR_SPACE_API_KEY=YOUR_KEY   # (optional) or paste in UI
streamlit run app.py
```

Then open the local URL shown (usually `http://localhost:8501`).

## 🖥️ Workflow
1. **Upload/Paste** → Paste messy text, upload CSV/XLSX, or drop a screenshot and run OCR.
2. **Review/Edit** → Fix terms/definitions in the grid. Watch live counts (8 per page).
3. **Download PDF** → Choose duplex mode, tweak back‑page offsets if alignment is off by a hair. Print duplex.

## 📝 Tips
- If colon `:` exists **inside parentheses**, we avoid splitting there.
- Spaced hyphen splitting only triggers on `␠-␠` (with spaces). For true minus signs in terms, use no spaces.
- For **short‑edge** duplex printers, choose *Short‑edge (rotate back 180°)*.
- Footer example: set Subject = *Science*, Unit = *Unit 1 Week 1*, Template = *Vocab*. Footer format `"{subject} • {unit}"` ⇒ `Science • Unit 1 Week 1`.

## 🔐 OCR Key
Use **OCR.space**. Do **not** commit keys to Git. Either set `OCR_SPACE_API_KEY` env var or paste in the sidebar field.

## 📄 License
MIT
