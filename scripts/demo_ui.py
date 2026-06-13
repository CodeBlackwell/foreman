import requests
import streamlit as st

API = "http://localhost:8001"
ABSTAIN_THRESHOLD = 0.70

DOMAIN_COLORS = {
    "Safety": "#ef4444",
    "Maintenance": "#3b82f6",
    "QualityControl": "#10b981",
}

ORIGIN_LABEL = {
    "official": "Official Standard",
    "ai": "AI Paraphrase",
    "user_edit": "User Edit",
}

EXAMPLE_QUESTIONS = [
    "How do I safely replace the bearing on press 4?",
    "What PPE is required for maintenance work?",
    "What are the post-repair tolerance specs?",
]


def score_bar(score: float) -> str:
    color = "#10b981" if score >= 0.85 else "#f59e0b" if score >= ABSTAIN_THRESHOLD else "#ef4444"
    pct = int(score * 100)
    return (
        f"<div style='display:flex;align-items:center;gap:8px'>"
        f"<div style='flex:1;background:#e5e7eb;border-radius:4px;height:6px'>"
        f"<div style='width:{pct}%;background:{color};height:6px;border-radius:4px'></div></div>"
        f"<span style='font-size:0.8em;color:{color};min-width:38px'>{score:.3f}</span>"
        f"</div>"
    )


def render_results() -> None:
    route_data = st.session_state.route_data
    retrieve_data = st.session_state.retrieve_data
    data = st.session_state.answer_data

    domain = route_data["entry_domain"]
    method = route_data["method"]
    color = DOMAIN_COLORS.get(domain, "#6b7280")
    st.markdown(
        f"**Entry domain:** <span style='color:{color};font-weight:600'>{domain}</span> "
        f"<span style='color:#6b7280;font-size:0.85em'>via {method} router</span>",
        unsafe_allow_html=True,
    )

    all_items = [
        item
        for section in retrieve_data.get("sections", [])
        for item in section["items"]
    ]
    all_items.sort(key=lambda x: x["similarity_score"], reverse=True)

    with st.expander(f"Retrieved evidence ({len(all_items)} chunks)", expanded=False):
        if retrieve_data.get("below_threshold"):
            st.warning(f"All chunks below abstain threshold ({ABSTAIN_THRESHOLD})")
        for item in all_items:
            d = item["domain"]
            c = DOMAIN_COLORS.get(d, "#6b7280")
            origin = ORIGIN_LABEL.get(item["origin"], item["origin"])
            st.markdown(
                f"<span style='color:{c};font-weight:600;font-size:0.85em'>{d}</span> "
                f"&nbsp;·&nbsp; **{item['doc_title']}** / {item['section_heading']} "
                f"<span style='color:#6b7280;font-size:0.8em'>({origin})</span>",
                unsafe_allow_html=True,
            )
            st.markdown(score_bar(item["similarity_score"]), unsafe_allow_html=True)
            st.caption(item["content"][:300] + ("…" if len(item["content"]) > 300 else ""))
            st.divider()

    response_type = data.get("response_type", "answered")
    notice = data.get("notice")

    if response_type == "out_of_domain":
        st.info(notice or "This question is outside the scope of the documentation.")
        return

    if notice:
        st.warning(notice)

    answer_text = data.get("answer_text", "")
    if not answer_text:
        return

    st.markdown("---")
    st.markdown(answer_text)

    citations = data.get("citations", [])
    if citations:
        with st.expander(f"Citations ({len(citations)})"):
            for cite in citations:
                origin = ORIGIN_LABEL.get(cite["origin"], cite["origin"])
                score = next(
                    (i["similarity_score"] for i in all_items
                     if i["doc_title"] == cite["doc_title"]
                     and i["section_heading"] == cite["section_heading"]),
                    None,
                )
                score_html = score_bar(score) if score is not None else ""
                source_url = cite.get("source_url")
                link_html = (
                    f" <a href='{source_url}' target='_blank' "
                    f"style='font-size:0.8em;color:#2563eb;text-decoration:none'>"
                    f"↗ view source</a>"
                    if source_url else ""
                )
                badges_html = " ".join(
                    f"<span style='background:{DOMAIN_COLORS.get(d,'#6b7280')};color:white;"
                    f"padding:1px 7px;border-radius:10px;font-size:0.75em;margin-right:3px'>{d}</span>"
                    for d in cite.get("domains", [])
                )
                st.markdown(
                    f"{badges_html} **{cite['doc_title']}** / {cite['section_heading']} "
                    f"<span style='color:#6b7280;font-size:0.85em'>({origin})</span>"
                    f"{link_html}",
                    unsafe_allow_html=True,
                )
                if score_html:
                    st.markdown(score_html, unsafe_allow_html=True)


st.set_page_config(page_title="foreman", page_icon="🏭", layout="centered")
st.title("foreman")
st.caption("Industrial floor supervisor retrieval system")

question = st.text_area(
    "Ask a question",
    placeholder="e.g. How do I safely replace the bearing on press 4?",
    height=80,
)

col1, col2 = st.columns([1, 3])
with col1:
    submit = st.button("Ask", type="primary", use_container_width=True)
with col2:
    selected = st.selectbox("Example questions", [""] + EXAMPLE_QUESTIONS, label_visibility="collapsed")

if selected and not question:
    question = selected

if submit and question.strip():
    st.session_state.pop("route_data", None)
    st.session_state.pop("retrieve_data", None)
    st.session_state.pop("answer_data", None)

    with st.spinner("Routing..."):
        try:
            r = requests.post(f"{API}/route", json={"question": question}, timeout=10)
            r.raise_for_status()
            st.session_state.route_data = r.json()
        except Exception as exc:
            st.error(f"Could not reach API: {exc}")
            st.stop()

    with st.spinner("Retrieving evidence..."):
        try:
            r = requests.post(
                f"{API}/retrieve",
                json={"question": question, "entry_domain": st.session_state.route_data["entry_domain"], "top_k": 3},
                timeout=30,
            )
            r.raise_for_status()
            st.session_state.retrieve_data = r.json()
        except Exception as exc:
            st.error(f"Retrieval failed: {exc}")
            st.stop()

    with st.spinner("Generating answer..."):
        try:
            r = requests.post(f"{API}/answer", json={"question": question}, timeout=60)
            r.raise_for_status()
            st.session_state.answer_data = r.json()
        except Exception as exc:
            st.error(f"Answer request failed: {exc}")
            st.stop()

elif submit:
    st.warning("Please enter a question.")

if "answer_data" in st.session_state:
    render_results()
