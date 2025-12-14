from pathlib import Path
import json

import streamlit as st
from streamlit.components.v1 import html


st.title("Reports")

mode = st.radio("Mode", ["Backtest", "Bot"], horizontal=True)

base_dir = Path("./out") / (mode.lower())

if not base_dir.exists():
    st.info(f"{base_dir} がまだありません。バックテスト / Bot を実行してください。")
    st.stop()

runs = sorted(
    [d for d in base_dir.iterdir() if d.is_dir()],
    key=lambda p: p.name,
    reverse=True,
)

if not runs:
    st.info("まだレポート対象のディレクトリがありません。")
    st.stop()

labels = [d.name for d in runs]
selected_label = st.selectbox("Run", labels)
selected_dir = runs[labels.index(selected_label)]

meta_path = selected_dir / "meta.json"
report_path = selected_dir / "quantstats_report.html"

st.write(f"選択中のディレクトリ: `{selected_dir}`")

if meta_path.exists():
    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    st.subheader("Run Config")
    st.write(f"Mode: `{meta.get('mode')}`  /  Type: `{meta.get('run_type')}`")
    st.write(f"Strategy: `{meta.get('strategy')}`")
    params = meta.get("params") or {}
    if params:
        st.write("Params:")
        st.json(params)
else:
    st.info("この実行のメタデータは保存されていません。")

if not report_path.exists():
    st.warning(
        f"{report_path} が見つかりません。レポートがまだ生成されていない可能性があります。"
    )
else:
    with report_path.open("r", encoding="utf-8") as f:
        content = f.read()

    style = """
<style>
body { background-color: #ffffff !important; color: #000000 !important; }
</style>
"""

    resize_script = """
<script>
function resizeParentIframe() {
  try {
    if (window.frameElement) {
      const h = document.body.scrollHeight + 100;
      window.frameElement.style.height = h + 'px';
    }
  } catch (e) {
    // ignore
  }
}
window.addEventListener('load', resizeParentIframe);
window.addEventListener('resize', resizeParentIframe);
</script>
"""

    if "<head>" in content:
        content = content.replace("<head>", f"<head>{style}", 1)
    else:
        content = style + content

    if "</body>" in content:
        content = content.replace("</body>", f"{resize_script}</body>", 1)
    else:
        content = content + resize_script

    html(content, height=0, scrolling=True)
