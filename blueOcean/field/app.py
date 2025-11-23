import streamlit as st

top_page = st.Page(page="./pages/top_page.py", title="Top", default=True)

nav = st.navigation([top_page])
nav.run()