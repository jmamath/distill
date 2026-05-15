# Credibility Source Data

Raw ranking files used to derive `source_credibility.json` for each topic.
These files are gitignored — only this README and the generated JSON are committed.

## Current source: ICLR 2026

**File:** `iclr2026_institutions_ranked_fractional.csv`

**What it is:** 5,356 accepted ICLR 2026 papers with PDF-derived institution
names, normalised to canonical forms. The fractional ranking gives each
institution 1/N credit per paper (where N = number of distinct institutions on
that paper).

**Where to get it:** Download the dataset from the source that produced it and
place the CSV here before running the generation script below.

## Regenerating source_credibility.json

From the project root with the virtualenv active:

```bash
source .venv/bin/activate
python3 - <<'EOF'
import csv, json, math
from pathlib import Path

csv_path = "data/credibility/iclr2026_institutions_ranked_fractional.csv"
out_path = "data/research_topics/data_advantage/source_credibility.json"

rows = []
with open(csv_path, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        rows.append((row["institution"], float(row["count"])))

max_count = rows[0][1]

def score(count):
    return max(1, round(10 * math.log(count + 1) / math.log(max_count + 1)))

result = {
    "_source": "ICLR 2026 accepted papers, fractional affiliation counting (1/N credit per institution per paper)",
    "_method": "fractional",
    "_scoring": f"log scale: max(1, round(10 * log(count+1) / log(max_count+1))); max_count={max_count} ({rows[0][0]})",
    "_total_institutions": len(rows),
}
for name, count in rows:
    result[name] = score(count)

Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(f"Written {len(rows)} institutions to {out_path}")
EOF
```

## Updating for a new conference year or topic

1. Place the new CSV in this directory.
2. Update `csv_path` and `_source` in the script above.
3. Run the script — it overwrites `source_credibility.json` in place.
4. Re-run `PYTHONPATH=src pytest tests/test_credibility.py` to confirm the JSON loads correctly.
