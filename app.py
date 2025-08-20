# --- FlashDecky bootstrap: ensure local module imports work in any layout ---
import os as _os, sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _THIS_DIR not in _sys.path:
    _sys.path.insert(0, _THIS_DIR)

# Prefer local fd_parsing; fall back to local parsing shim
try:
    from fd_parsing import parse_free_text, parse_table_guess  # type: ignore
except Exception:  # pragma: no cover
    from parsing import parse_free_text, parse_table_guess  # type: ignore

import io
import os
import streamlit as st
import pandas as pd

from pdf_engine import build_flashcards_pdf
from ocr_client import ocr_image_to_text
from utils import validate_cards_df, live_counts

st.set_page_config(page_title="FlashDecky — Instant Flash Cards", page_icon="📇", layout="wide")

if "cards" not in st.session_state:
    st.session_state.cards = pd.DataFrame(columns=["Front", "Back"])

st.title("📇 FlashDecky — Instant Flash Cards")
st.caption("Paste text, upload CSV/XLSX, or drop a screenshot → review → print-ready PDF (8 per page).")

with st.sidebar:
    st.header("⚙️ Settings")
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
    offset_x_mm = st.number_input("Back page offset X (mm)", value=0.0, step=0.5)
    offset_y_mm = st.number_input("Back page offset Y (mm)", value=0.0, step=0.5)
    show_corner_markers = st.checkbox("Corner markers", value=False)

    st.divider()
    st.subheader("Card footer")
    show_footer = st.checkbox("Show footer on each card", value=False, help="Printed inside each card box, front & back.")
    subject = st.text_input("Subject", value="")
    lesson = st.text_input("Lesson", value="")
    footer_choice = st.selectbox("Footer format", options=["{subject} • {lesson}", "{lesson} • {subject}"], index=0)

    st.divider()
    st.subheader("Text rendering")
    base_term_size = st.slider("Front font size (pt)", min_value=10, max_value=36, value=20)
    base_def_size = st.slider("Back font size (pt)", min_value=10, max_value=20, value=14)

# Prefer Streamlit Secrets for OCR key, fallback to env var
OCR_KEY = st.secrets.get("OCR_SPACE_API_KEY", os.getenv("OCR_SPACE_API_KEY", ""))

st.markdown("### 1) Upload / Paste")

tabs = st.tabs(["Paste text", "Upload CSV/TSV/XLSX", "Screenshot"])

with tabs[0]:
    st.write("**Paste free-form text** (plain lines, lists, or `term - definition` / `term : definition`).")
    sample = (
        "munch - to chew food loudly and completely\n"
        "bellowed: to have shouted in a loud deep voice\n"
        "rough - when you do something in a way that is not gentle.\n"
        "handle - when you are not able to deal with something\n"
        "cool - to calm down\n"
        "bounce - to move up and down\n"
        "grinned - to smile a wide smile\n"
        "might - to do something with all your power.\n"
    )
    pasted = st.text_area("Paste here", value=sample, height=220)
    if st.button("Review front & back of flash cards", type="primary"):
        records, warnings = parse_free_text(pasted)
        df = pd.DataFrame(records, columns=["Front", "Back"]) if records else pd.DataFrame(columns=["Front", "Back"])
        st.session_state.cards = df
        for w in warnings:
            st.warning(w)
        st.success(f"Upload complete. Parsed {len(df)} cards.")

with tabs[1]:
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
                st.success(f"Upload complete. Loaded {len(cards_df)} cards from table.")
        else:
            st.info("Upload a file to begin. Ensure it has at least two columns.")

with tabs[2]:
    st.write("**Drop a PNG/JPG screenshot.** Text will be auto-extracted.")
    img = st.file_uploader("Upload screenshot (PNG/JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=False)
    extracted_text = ""
    if img is not None:
        if not OCR_KEY:
            st.error("No OCR key found. Add OCR_SPACE_API_KEY to Streamlit Secrets (Settings → Secrets).")
        else:
            with st.spinner("Extracting text…"):
                ok, extracted_text, err = ocr_image_to_text(img.read(), api_key=OCR_KEY)
            if ok:
                st.success("Upload complete.")
            else:
                st.error(f"OCR failed: {err}")

    if img is not None and extracted_text:
        edited = st.text_area("Extracted text (editable)", value=extracted_text, height=220)
        if st.button("Review front & back of flash cards", key="btn_parse_ocr", type="primary"):
            records, warnings = parse_free_text(edited)
            df = pd.DataFrame(records, columns=["Front", "Back"]) if records else pd.DataFrame(columns=["Front", "Back"])
            st.session_state.cards = df
            for w in warnings:
                st.warning(w)
            st.success(f"Upload complete. Parsed {len(df)} cards.")

st.markdown("### 2) Review & Edit")
cards = st.session_state.cards.copy()
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

n_cards, n_sheets = live_counts(st.session_state.cards)
c1, c2 = st.columns(2)
with c1:
    st.metric("Total cards", n_cards)
with c2:
    st.metric("Sheets @ 8 per page", n_sheets)
invalid_rows = validate_cards_df(st.session_state.cards)
if invalid_rows:
    st.error("Some rows need attention (empty Front/Back):")
    st.code(", ".join(str(i+1) for i in invalid_rows))

st.markdown("### 3) Download PDF")
if st.button("🖨️ Generate PDF", type="primary", disabled=len(st.session_state.cards)==0):
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
            footer_template=footer_choice,
            subject=subject,
            lesson=lesson,
            base_term_size=base_term_size,
            base_def_size=base_def_size,
        )
        buffer.seek(0)
        st.download_button("Download FlashDecky.pdf", data=buffer, file_name="FlashDecky.pdf", mime="application/pdf")
        st.success("PDF ready. If backs are off a hair, tweak the back-page offsets in mm.")
