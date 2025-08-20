FlashDecky Beta Parser Patch
----------------------------
This patch replaces the parser with the Beta approach (regex + continuation lines).

Files included:
- parsing.py
- fd_parsing.py  (identical; provided in case your app imports fd_parsing)

How to apply:
1) Drop BOTH files into the same folder as your app.py (overwrite existing parsing module).
2) Restart Streamlit.
No other files need changes.
