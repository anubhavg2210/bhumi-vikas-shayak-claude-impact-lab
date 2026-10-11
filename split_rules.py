<<<<<<< HEAD
"""Split the MP Bhumi Vikas Rules 2012 (English, pdftotext -layout output) into
one JSON record per rule, keeping the PDF page each rule starts and ends on.

Usage: python3 -I split_rules.py <bvn_layout.txt> <out.jsonl>

A heading is 'N. Title.-' (or 'N-A. Title.-') at the start of a line. Rule
numbers must rise, so numbered rows inside tables are not taken as rules."""
import json, re, sys

src, out = sys.argv[1], sys.argv[2]
# Amended rules start with '[', some put '(1)' before the title, and a few titles
# wrap onto the next line (ending in a comma), so all three forms are accepted.
HEAD = re.compile(r"^\s{0,12}\[?(\d{1,3})(-[A-Z])?\.\s*(?:\(\d+\)\s*)?\[?([A-Z][^\n]{2,140}?)\s*[.\]]?\s*(?:-{1,2}|—|–|,\s*$)")
# Bracketed amended headings sometimes wrap with no closing mark. Accept them only
# when the number is exactly the next one, so table rows are never mistaken for rules.
LOOSE = re.compile(r"^\s{0,12}\[(\d{1,3})(-[A-Z])?\.\s*([A-Z][^\n]{5,140})$")
PART = re.compile(r"^\s*PART\s*[-–]\s*([IVX]+)\s*:?\s*(.*)$", re.I)

text = open(src, encoding="utf-8", errors="replace").read()
rules, cur, last, part = [], None, 0, ""
for page_no, page in enumerate(text.split("\f"), start=1):
    for line in page.split("\n"):
        pm = PART.match(line)
        if pm:
            part = f"Part {pm.group(1).upper()}: {pm.group(2).strip().title()}"
        m = HEAD.match(line)
        if not m:
            lm = LOOSE.match(line)
            if lm and int(lm.group(1)) == last + 1:
                m = lm
        if m:
            n = int(m.group(1))
            suffix = m.group(2) or ""
            # accept the next number (allowing small gaps for deleted rules) or an -A/-B variant
            if (0 < n - last <= 3) or (suffix and n == last):
                if cur: rules.append(cur)
                cur = dict(rule=f"{n}{suffix}", title=m.group(3).strip().rstrip(".-"),
                           part=part, page_start=page_no, page_end=page_no, text=line.strip())
                last = n
                continue
        if cur:
            cur["text"] += "\n" + line.rstrip()
            cur["page_end"] = page_no
if cur: rules.append(cur)
for r in rules:
    r["text"] = re.sub(r"\n{3,}", "\n\n", r["text"]).strip()
if len(rules) < 50:
    # Guard: the 2025 consolidated PDF has 90+ rules. Far fewer means the layout changed.
    sys.exit(f"Only {len(rules)} rules found. Check the source layout before using the output.")
with open(out, "w", encoding="utf-8") as f:
    for r in rules: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{len(rules)} rules, last = rule {rules[-1]['rule']} on page {rules[-1]['page_start']}")
=======
"""Split the MP Bhumi Vikas Rules 2012 (English, pdftotext -layout output) into
one JSON record per rule, keeping the PDF page each rule starts and ends on.

Usage: python3 -I split_rules.py <bvn_layout.txt> <out.jsonl>

A heading is 'N. Title.-' (or 'N-A. Title.-') at the start of a line. Rule
numbers must rise, so numbered rows inside tables are not taken as rules."""
import json, re, sys

src, out = sys.argv[1], sys.argv[2]
# Amended rules start with '[', some put '(1)' before the title, and a few titles
# wrap onto the next line (ending in a comma), so all three forms are accepted.
HEAD = re.compile(r"^\s{0,12}\[?(\d{1,3})(-[A-Z])?\.\s*(?:\(\d+\)\s*)?\[?([A-Z][^\n]{2,140}?)\s*[.\]]?\s*(?:-{1,2}|—|–|,\s*$)")
# Bracketed amended headings sometimes wrap with no closing mark. Accept them only
# when the number is exactly the next one, so table rows are never mistaken for rules.
LOOSE = re.compile(r"^\s{0,12}\[(\d{1,3})(-[A-Z])?\.\s*([A-Z][^\n]{5,140})$")
PART = re.compile(r"^\s*PART\s*[-–]\s*([IVX]+)\s*:?\s*(.*)$", re.I)

text = open(src, encoding="utf-8", errors="replace").read()
rules, cur, last, part = [], None, 0, ""
for page_no, page in enumerate(text.split("\f"), start=1):
    for line in page.split("\n"):
        pm = PART.match(line)
        if pm:
            part = f"Part {pm.group(1).upper()}: {pm.group(2).strip().title()}"
        m = HEAD.match(line)
        if not m:
            lm = LOOSE.match(line)
            if lm and int(lm.group(1)) == last + 1:
                m = lm
        if m:
            n = int(m.group(1))
            suffix = m.group(2) or ""
            # accept the next number (allowing small gaps for deleted rules) or an -A/-B variant
            if (0 < n - last <= 3) or (suffix and n == last):
                if cur: rules.append(cur)
                cur = dict(rule=f"{n}{suffix}", title=m.group(3).strip().rstrip(".-"),
                           part=part, page_start=page_no, page_end=page_no, text=line.strip())
                last = n
                continue
        if cur:
            cur["text"] += "\n" + line.rstrip()
            cur["page_end"] = page_no
if cur: rules.append(cur)
for r in rules:
    r["text"] = re.sub(r"\n{3,}", "\n\n", r["text"]).strip()
if len(rules) < 50:
    # Guard: the 2025 consolidated PDF has 90+ rules. Far fewer means the layout changed.
    sys.exit(f"Only {len(rules)} rules found. Check the source layout before using the output.")
with open(out, "w", encoding="utf-8") as f:
    for r in rules: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{len(rules)} rules, last = rule {rules[-1]['rule']} on page {rules[-1]['page_start']}")
>>>>>>> 4be0899 (feat: add Bhumi Vikas Sahayak backend RAG)
