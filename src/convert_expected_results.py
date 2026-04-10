import json
from pathlib import Path

input_path = Path("../expected_results/02_gcd_lcm_results.txt")
output_path = Path("../expected_results/02_gcd_lcm_results.json")

items = []
with input_path.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        # split on ":", then strip spaces from each part
        parts = [p.strip() for p in line.split(":")]
        if len(parts) != 3:
            raise ValueError(f"Unexpected line format: {line}")
        name, type_, occurrences = parts
        items.append({
            "name": name,
            "type": type_,
            "occurrences": int(occurrences),
        })

with output_path.open("w", encoding="utf-8") as out:
    json.dump(items, out, indent=2)

print(f"Wrote {len(items)} entries to {output_path}")