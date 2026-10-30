import json, random, time
from app.answer import ask

random.seed(0)
answerable = [json.loads(l)["q"] for l in open("eval/questions.jsonl") if l.strip()]
answerable = random.sample(answerable, 25)
unanswerable = [json.loads(l)["q"] for l in open("eval/unanswerable.jsonl") if l.strip()]


def run(q):
    err = None
    for wait in (0, 10, 30):  # retry on Groq rate limits
        time.sleep(wait)
        try:
            r = ask(q)
            time.sleep(2)
            return r
        except Exception as e:
            err = e
    print("ERROR", q, err)
    return None


total = supported = answered = errors = 0
rows = []
for q in answerable:
    r = run(q)
    if r is None:
        errors += 1
        continue
    answered += bool(r["claims"])
    for c in r["claims"]:
        total += 1
        supported += c["supported"]
        cited = "\n".join(r["sources"][n - 1]["text"] for n in c["cites"] if 1 <= n <= len(r["sources"]))
        rows.append({"q": q, "claim": c["text"], "cites": c["cites"], "supported": c["supported"], "cited_text": cited})

raw_refuse = final_refuse = 0
for q in unanswerable:
    r = run(q)
    if r is None:
        errors += 1
        continue
    raw_refuse += not r["claims"]
    final_refuse += r["verified_answer"] == "I don't know."

with open("eval/claims_out.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

n = len(unanswerable)
print(f"errors: {errors}")
print(f"faithfulness (answerable): {supported}/{total} claims supported = {supported / max(total, 1):.2f}")
print(f"answerable questions with an answer: {answered}/{len(answerable)}")
print(f"refusal, model returned no claims: {raw_refuse}/{n}")
print(f"refusal, final answer is I don't know: {final_refuse}/{n}")