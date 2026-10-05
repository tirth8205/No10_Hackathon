"""Build an unseen-style test set: the same facts and the same gaps as synthetic
cases, rewritten by the model in registers the rules have never seen. Labels
carry over by construction. Used ONLY after tuning, as a generalisation check.

    python -m eval.style_shift --n 40 --out data/style_shift_cases.json
    python -m eval.run_eval --set style --votes 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from pydantic import BaseModel

from engine.llm import OpenAILLM

ROOT = Path(__file__).resolve().parent.parent

STYLES = [
    "an informal email from the author to the solicitor, first person, short paragraphs, no letterhead",
    "a formal letter with a letterhead, reference numbers, a date line and 'Yours faithfully'",
    "a bullet-point summary written in haste, fragments rather than full sentences",
    "a letter by a writer whose first language is not English: slightly unusual grammar and word choice, but the meaning clear",
    "a long letter with two or three unrelated paragraphs of padding (office hours, how to contact the service, general information) around the substance",
    "the same content with every sentence reordered and reworded using synonyms, keeping all names, dates and figures identical",
]


class Rewrite(BaseModel):
    text: str
    preserved_everything: bool
    notes: str


PROMPT = """Rewrite the document below as {style}.

Rules, all strict:
- Keep every fact: all names, roles, organisations, dates, reference numbers, offences, amounts and places exactly as they are.
- Keep the MEANING of every statement. If the original confirms something, the rewrite confirms it in different words. If the original hedges ("might be", "may be"), the rewrite must hedge in the same way. If the original omits something (for example it never names the perpetrator, never gives a date, never says why support was needed), the rewrite must omit it too. Do not add facts, do not fill gaps, do not remove gaps.
- Do not add any statement about meeting legal aid requirements.
- Return the rewritten document as text, and set preserved_everything to false if you could not follow these rules for any reason, explaining why in notes.

<document>
{text}
</document>"""


async def main_async(n: int, out: Path, seed: int, model: str | None) -> None:
    cases = json.load(open(ROOT / "data" / "synthetic_cases.json"))["cases"]
    rng = random.Random(seed)
    # stratify: round-robin across paragraphs so no paragraph dominates
    by_para: dict[str, list] = {}
    for c in cases:
        if len(c["documents"]) != 1:
            continue
        by_para.setdefault(c["documents"][0]["claimed_para"], []).append(c)
    for v in by_para.values():
        rng.shuffle(v)
    picked = []
    while len(picked) < n and any(by_para.values()):
        for p in list(by_para):
            if by_para[p] and len(picked) < n:
                picked.append(by_para[p].pop())
    llm = OpenAILLM(model=model)
    sem = asyncio.Semaphore(8)

    async def one(case, i):
        style = STYLES[i % len(STYLES)]
        d = case["documents"][0]
        async with sem:
            rw: Rewrite = await llm._parse(PROMPT.format(style=style, text=d["text"]), Rewrite,
                                          system="You rewrite documents faithfully for software testing. You never change facts or add or remove information.")
        if not rw.preserved_everything:
            print("dropped", case["id"], "-", rw.notes[:120])
            return None
        new = json.loads(json.dumps(case))
        new["id"] = f"S-{case['id']}"
        new["source"] = "style_shift"
        new["category"] = "style_shift"
        new["style"] = style
        new["base_id"] = case["id"]
        new["documents"][0]["text"] = rw.text
        return new

    results = [r for r in await asyncio.gather(*[one(c, i) for i, c in enumerate(picked)]) if r]
    out.write_text(json.dumps({"meta": {"description": "Synthetic cases rewritten in unseen styles; labels inherited from the base case. Generated after rule tuning as a generalisation check.",
                                        "n_cases": len(results), "styles": STYLES, "model": llm.name},
                               "cases": results}, indent=2, ensure_ascii=False))
    print(f"wrote {len(results)} cases to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=str(ROOT / "data" / "style_shift_cases.json"))
    a = ap.parse_args()
    asyncio.run(main_async(a.n, Path(a.out), a.seed, a.model))
