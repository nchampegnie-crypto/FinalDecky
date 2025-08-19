import io
import os
from typing import List, Tuple
import streamlit as st
import pandas as pd

from parsing import parse_free_text, parse_table_guess
from pdf_engine import build_flashcards_pdf
from ocr_client import ocr_image_to_text
from utils import validate_cards_df, live_counts

st.set_page_config(page_title="FlashDecky — Instant Flash Cards", page_icon="📇", layout="wide")

if "cards" not in st.session_state:
    st.session_state.cards = pd.DataFrame(columns=["Front", "Back"])  # canonical schema
if "stage" not in st.session_state:
    st.session_state.stage = 1

st.title("📇 FlashDecky — Instant Flash Cards")
st.caption("Paste text, upload CSV/XLSX, or drop a screenshot → review → print‑ready PDF (8 per page).")

with st.sidebar:
    st.header("⚙️ Settings")
    # Duplex options
    duplex_mode = st.selectbox(
        "Back/front alignment",
        options=[
            "Long-edge mirrored (default)",
            "Long-edge non-mirrored",
            "Short-edge (rotate back 180°)",
        ],
        index=0,
        help="Choose how your printer flips paper. 'Long-edge mirrored' works for most duplex printers."
    )
    offset_x_mm = st.number_input("Back page offset X (mm)", value=0.0, step=0.5, help="Fine-tune horizontal drift on the back side.")
    offset_y_mm = st.number_input("Back page offset Y (mm)", value=0.0, step=0.5, help="Fine-tune vertical drift on the back side.")
    show_corner_markers = st.checkbox("Corner markers", value=False)

    st.divider()
    st.subheader("Footer / metadata")
    show_footer = st.checkbox("Show footer on pages", value=False)
    subject = st.text_input("Subject", value="")
    unit = st.text_input("Unit/Lesson", value="")
    template_name = st.text_input("Template", value="")
    footer_template = st.text_input(
        "Footer format (placeholders: {subject} {unit} {lesson} {page})",
        value="{subject} • {unit}",
    )

    st.divider()
    st.subheader("Text rendering")
    base_term_size = st.slider("Front font size (pt)", min_value=10, max_value=36, value=20)
    base_def_size = st.slider("Back font size (pt)", min_value=10, max_value=20, value=14)

    st.divider()
    st.subheader("OCR (optional)")
    ocr_enabled = st.checkbox("Enable OCR for screenshots (PNG/JPG)", value=False)
    ocr_api_key = st.text_input(
        "OCR.space API key",
        value=os.getenv("OCR_SPACE_API_KEY", ""),
        type="password",
        help="Provide your OCR.space API key to extract text from screenshots."
    )

st.markdown("""
### 1) Upload / Paste
Use one of the tabs below. FlashDecky understands free‑form text, bullet/numbered lists, dictionary style entries, CSV/TSV, and XLSX.
""")

input_tabs = st.tabs(["Paste text", "Upload CSV/TSV/XLSX", "Screenshot → OCR"])  # Step 1

with input_tabs[0]:
    st.write("**Paste free‑form text** (plain lines, numbered/bulleted lists, or `term : definition`).")
    sample = (
        "abhor (v.) : to hate, detest\n"
        "benevolent (adj.) : well meaning; kindly\n\n"
        "1) photosynthesis — process by which plants make food\n"
        "- mitosis - cell division into two daughter cells\n"
        "Solar system\tSun and its planets\n"
    )
    pasted = st.text_area("Paste here", value=sample, height=220)
    if st.button("Parse pasted text", type="primary"):
        records, warnings = parse_free_text(pasted)
        df = pd.DataFrame(records, columns=["Front", "Back"]) if records else pd.DataFrame(columns=["Front", "Back"]) 
        st.session_state.cards = df
        if warnings:
            for w in warnings:
                st.warning(w)
        st.success(f"Parsed {len(df)} cards.")
        st.session_state.stage = 2

with input_tabs[1]:
    st.write("**Upload a table** (CSV, TSV, or XLSX). Then map which columns = Front vs Back.")
    up = st.file_uploader("Upload CSV/TSV/XLSX", type=["csv", "tsv", "xlsx"], accept_multiple_files=False)
    if up is not None:
        df_preview, cols = parse_table_guess(up)
        if df_preview is not None and len(cols) >= 2:
            st.dataframe(df_preview.head(20), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                front_col = st.selectbox("Front column", options=cols, index=0)
            with c2:
                back_col = st.selectbox("Back column", options=cols, index=1)
            if st.button("Use selected columns", type="primary"):
                cards_df = df_preview[[front_col, back_col]].copy()
                cards_df.columns = ["Front", "Back"]
                st.session_state.cards = cards_df
                st.success(f"Loaded {len(cards_df)} cards from table.")
                st.session_state.stage = 2
        else:
            st.info("Upload a file to begin. Ensure it has at least two columns.")

with input_tabs[2]:
    st.write("**Drop a PNG/JPG screenshot.** Optionally run OCR to extract text (shows editable box).")
    img = st.file_uploader("Upload screenshot (PNG/JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=False)
    extracted_text = ""
    if img is not None and ocr_enabled:
        if not ocr_api_key:
            st.error("Please provide your OCR.space API key in the sidebar.")
        else:
            with st.spinner("Running OCR..."):
                ok, extracted_text, err = ocr_image_to_text(img.read(), api_key=ocr_api_key)
            if ok:
                st.success("OCR complete. Review or edit the extracted text below.")
            else:
                st.error(f"OCR failed: {err}")
    if img is not None and not ocr_enabled:
        st.info("OCR disabled. Enable it in the sidebar to extract text, or paste text manually.")

    if img is not None and (extracted_text or ocr_enabled):
        edited = st.text_area("Extracted text (editable)", value=extracted_text, height=200)
        if st.button("Parse extracted text", type="primary"):
            records, warnings = parse_free_text(edited)
            df = pd.DataFrame(records, columns=["Front", "Back"]) if records else pd.DataFrame(columns=["Front", "Back"]) 
            st.session_state.cards = df
            if warnings:
                for w in warnings:
                    st.warning(w)
            st.success(f"Parsed {len(df)} cards from OCR text.")
            st.session_state.stage = 2

st.markdown("""
### 2) Review & Edit
Use the grid to fix any rows. You can add/delete rows and bulk‑paste. The **Validation** panel flags empty Front/Back.
""")

cards = st.session_state.cards.copy()

col_left, col_right = st.columns([3, 2])
with col_left:
    edited = st.data_editor(
        cards,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Front": st.column_config.TextColumn("Front of Card (term)", required=True),
            "Back": st.column_config.TextColumn("Back of Card (definition)", required=True),
        },
        key="editor",
    )
    st.session_state.cards = edited

with col_right:
    n_cards, n_sheets = live_counts(st.session_state.cards)
    st.metric("Total cards", n_cards)
    st.metric("Sheets @ 8 per page", n_sheets)

    invalid_rows = validate_cards_df(st.session_state.cards)
    if invalid_rows:
        st.error("Some rows need attention (empty Front/Back):")
        st.code(", ".join(str(i+1) for i in invalid_rows))

    st.subheader("Preview (first 8)")
    preview_df = st.session_state.cards.head(8)
    for idx, row in preview_df.iterrows():
        st.markdown(f"**{idx+1}. {row['Front']}**\n\n{row['Back']}")

st.markdown("""
### 3) Download PDF
Generates a **two‑page PDF per sheet** (front then back) with dashed cut lines and alignment options for duplex printing.
""")

c1, c2 = st.columns([1,2])
with c1:
    gen = st.button("🖨️ Generate PDF", type="primary", disabled=len(st.session_state.cards)==0)

with c2:
    if gen:
        if len(st.session_state.cards) == 0:
            st.warning("No cards to print.")
        else:
            buffer = io.BytesIO()
            build_flashcards_pdf(
                buffer,
                st.session_state.cards,
                duplex_mode=duplex_mode,
                offset_x_mm=offset_x_mm,
                offset_y_mm=offset_y_mm,
                show_corner_markers=show_corner_markers,
                show_footer=show_footer,
                footer_template=footer_template,
                subject=subject,
                unit=unit,
                lesson=template_name,
                base_term_size=base_term_size,
                base_def_size=base_def_size,
            )
            buffer.seek(0)
            st.download_button(
                "Download FlashDecky.pdf",
                data=buffer,
                file_name="FlashDecky.pdf",
                mime="application/pdf",
            )
            st.success("PDF ready. Use duplex printing. If backs are off a hair, tweak the back‑page offsets in mm.")
