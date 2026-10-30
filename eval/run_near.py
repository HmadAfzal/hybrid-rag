import json, time
from app.answer import ask

qs = [json.loads(l)["q"] for l in open("eval/nearmiss.jsonl") if l.strip()]
raw = final = 0
for q in qs:
    r = ask(q)
    time.sleep(2)
    raw += not r["claims"]
    final += r["verified_answer"] == "I don't know."
    if r["verified_answer"] != "I don't know.":
        print("ANSWERED:", q, "\n ", r["verified_answer"], "\n")
print(f"refusal, no claims: {raw}/{len(qs)}")
print(f"refusal, final: {final}/{len(qs)}")