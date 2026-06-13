#!/usr/bin/env python3
import json
import urllib.request

API = "http://localhost:8001"


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get(path: str) -> str:
    with urllib.request.urlopen(f"{API}{path}") as resp:
        raw = resp.read()
        try:
            return json.dumps(json.loads(raw), indent=2)
        except Exception:
            return raw.decode()


def hr(label: str) -> None:
    print(f"\n--- {label} ---")


def sep() -> None:
    print("\n==========================================")


sep()
print("  foreman demo — route-then-traverse QA")
sep()

hr("health")
print(get("/health"))

hr("route: safety query")
print(json.dumps(post("/route", {"question": "how do I apply LOTO before working on the press?"}), indent=2))

hr("route: maintenance query")
print(json.dumps(post("/route", {"question": "how do I replace the drive bearing?"}), indent=2))

hr("answer: cross-domain bearing replacement (routes Maintenance → Safety + QC)")
r = post("/answer", {"question": "How do I safely replace the bearing on press 4?"})
print(f"response_type: {r['response_type']}")
if r.get("notice"):
    print(f"notice: {r['notice']}")
print(f"\n{r['answer_text'][:600]}")
print("\ncitations:")
for c in r["citations"]:
    badges = " ".join(f"[{d}]" for d in c["domains"])
    print(f"  {badges} [{c['origin']}] {c['doc_title']} / {c['section_heading']}")

hr("abstain policy")
print(get("/answer/abstain-policy"))
