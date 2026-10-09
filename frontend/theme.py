"""Scoped styling: native controls keep explicit, readable foreground colours."""

CSS = """
<style>
:root {
  --pulse-ink: #15364a;
  --pulse-muted: #536c7d;
  --pulse-teal: #087f89;
  --pulse-border: #d9e5eb;
}
.stApp { background: #fafcfd; color: var(--pulse-ink); font-family: "Source Sans", "Source Sans Pro", sans-serif; }
[data-testid="stMainBlockContainer"] {
  max-width: 1480px;
  padding: 2rem 2rem 2rem;
  container-type: inline-size;
  container-name: workspace;
}
h1,h2,h3 { color: var(--pulse-ink); letter-spacing: -.015em; font-weight: 700; }
h1 { font-size: clamp(1.6rem, 2.2vw, 2rem); line-height: 1.2; padding-bottom: .35rem; }
h3 { font-size: 1.1rem; }
.st-key-workspace-nav { margin-bottom: .6rem; border-bottom: 1px solid var(--pulse-border); }
.st-key-workspace-nav [role="radiogroup"] { display: flex; flex-wrap: wrap; gap: .25rem 1rem; }
.st-key-workspace-nav [role="radiogroup"] label {
  margin: 0; padding: .7rem .6rem; border-bottom: 3px solid transparent;
  cursor: pointer; border-radius: 4px 4px 0 0;
}
.st-key-workspace-nav [role="radiogroup"] label > div:first-child { display: none; }
.st-key-workspace-nav [role="radiogroup"] label p { color: #536c7d; font-weight: 600; white-space: nowrap; }
.st-key-workspace-nav [role="radiogroup"] label:hover { background: #edf6f6; }
.st-key-workspace-nav [role="radiogroup"] label:has(input:checked) { border-color: #087f89; background: #edf7f7; }
.st-key-workspace-nav [role="radiogroup"] label:has(input:checked) p { color: #08717b; }
.st-key-workspace-nav [role="radiogroup"] label:has(input:focus-visible) { outline: 2px solid #54bbc4; }
[data-testid="stMain"] [data-testid="stCaptionContainer"] { color: var(--pulse-muted); }
[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
  color: #294c60; font-weight: 600; font-size: .85rem;
}
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] {
  background: white; border-color: #cbdce5; border-radius: 8px;
}
[data-testid="stSidebar"] {
  background: #0c505d;
  color: #f5ffff;
  border-right: 1px solid #0a4450;
}
[data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #edf9fa; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: #c7dfe4; opacity: 1; font-size: .8rem; line-height: 1.5;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: #dfedef; font-weight: 600;
}
[data-testid="stSidebar"] h3 { color: #edf9fa; }
[data-testid="stSidebar"] .st-key-filters { padding: 0; background: transparent; border: 0; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] { background: #f5fafc; color: #15364a; border-color: #cbdce5; }
[data-testid="stSidebar"] [data-baseweb="tag"] { color: #15364a; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .35rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: .65rem .7rem; border-radius: 8px; border: 1px solid transparent;
  width: 100%; margin: 0; transition: background .15s;
}
[data-testid="stSidebar"] [role="radiogroup"] label p { color: #f2ffff; font-weight: 500; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #176674; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: #16838d; border-color: #36a6ad;
}
[data-testid="stSidebar"] .stButton button {
  background: #fff; color: #174b59; border: 1px solid #d0e3e8;
  min-height: 2.7rem; font-weight: 600;
}
[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] { color: inherit; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #c7dfe4; }
[data-testid="stSidebar"] .stButton button p,
[data-testid="stSidebar"] [data-testid="stFileUploader"] button p { color: inherit; }
[data-testid="stSidebar"] .stButton button:hover:not(:disabled) {
  background: #e5f4f6; border-color: #a6cfd6; color: #113c49;
}
[data-testid="stSidebar"] .stButton button:disabled {
  background: #275f6b; color: #c2d8de; border-color: #477d87; opacity: 1;
}
[data-testid="stSidebar"] .stButton button[kind="primary"] {
  background: #14949e; color: #fff; border-color: #3eb1b8;
}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
  background: #10838e; color: #fff;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
  background: #f5fafc; border: 1px solid #d3e5eb; border-radius: 12px; padding: .8rem;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stFileUploader"] section,
[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
  color: #294f63;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
  background: #edf6f9; border-radius: 8px;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
  color: #174b59; background: #fff; border: 1px solid #bfd6df;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] svg { color: #416b7d; }
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button { color: #eaf9fa; }
[data-testid="stSidebar"] hr { border-color: #37727d; }
.stButton button, .stDownloadButton button { border-radius: 8px; min-height: 2.5rem; }
button:focus-visible, input:focus-visible {
  outline: 3px solid #54bbc4; outline-offset: 2px;
}
[data-testid="stMetric"] {
  background: #fff; border: 1px solid var(--pulse-border); border-radius: 12px;
  padding: 1rem 1.15rem;
}
[data-testid="stMetricLabel"] p {
  color: #496576; font-size: .8rem; font-weight: 600; white-space: normal;
}
[data-testid="stMetricValue"] { color: #15364a; font-weight: 700; }
[data-testid="stVerticalBlockBorderWrapper"] > div {
  background: white; border-color: var(--pulse-border); border-radius: 12px;
  box-shadow: none;
}
.st-key-filters { padding: .9rem 1rem; background: #fff; border: 1px solid var(--pulse-border); border-radius: 12px; }
.brand { color: #fff; font-size: 1.35rem; font-weight: 750; line-height: 1.3; margin: 0 0 1.2rem; }
.brand span { color: #9de0e1; font-size: 1.9rem; margin-right: .5rem; }
.pill {
  display: inline-block; background: #e1f2f2; color: #1a606b; border: 1px solid #cce7e8;
  border-radius: 20px; padding: 5px 12px; font-size: .75rem; font-weight: 600; margin-bottom: .5rem;
}
[data-testid="stChatMessage"] { background: #edf5f9; border: 1px solid #dfeaf0; border-radius: 12px; }
[data-testid="stChatInput"] { border-color: #b9d4df; border-radius: 10px; background: #fff; }
[data-testid="stColumn"], [data-testid="stPlotlyChart"] { min-width: 0; }
@container workspace (max-width: 1050px) {
  .st-key-filters [data-testid="stHorizontalBlock"],
  .st-key-metrics [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 1rem; }
  .st-key-filters [data-testid="stColumn"],
  .st-key-metrics [data-testid="stColumn"] {
    flex: 1 1 calc(50% - 1rem) !important; width: calc(50% - 1rem) !important; min-width: 0 !important;
  }
}
@container workspace (max-width: 850px) {
  .st-key-overview-primary [data-testid="stHorizontalBlock"],
  .st-key-overview-secondary [data-testid="stHorizontalBlock"],
  .st-key-chat-layout [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 1rem; }
  .st-key-overview-primary [data-testid="stColumn"],
  .st-key-overview-secondary [data-testid="stColumn"],
  .st-key-chat-layout [data-testid="stColumn"] {
    flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important;
  }
}
@container workspace (max-width: 480px) {
  .st-key-workspace-nav [role="radiogroup"] { gap: 0; }
  .st-key-workspace-nav [role="radiogroup"] label { flex: 1 1 auto; padding: .65rem .45rem; }
  .st-key-workspace-nav [role="radiogroup"] label p { font-size: .9rem; }
  .st-key-filters [data-testid="stColumn"] {
    flex: 1 1 100% !important; width: 100% !important;
  }
  [data-testid="stMetric"] { padding: .8rem; }
  [data-testid="stMetricValue"] { font-size: 1.65rem; }
}
@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"] { padding: 3.5rem 1rem 1.5rem; }
  h1 { font-size: 1.65rem; }
  [data-testid="stSidebar"] { max-width: min(20rem, 90vw); }
  .brand { font-size: 1.2rem; }
  [data-testid="stChatInput"] textarea { font-size: 1rem; }
}
</style>
"""
