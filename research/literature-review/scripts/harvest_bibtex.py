"""Extract BibTeX entries from research report markdown files, dedupe by key,
and write a merged bibliography.bib."""
import glob
import re

entries = {}
pattern = re.compile(r"@(\w+)\{([^,]+),")

for path in sorted(glob.glob("/home/ubuntu/pfe/research/*.md")):
    text = open(path).read()
    # find each @type{key, ... } block by brace matching
    for m in pattern.finditer(text):
        start = m.start()
        depth = 0
        end = None
        for i in range(start, min(len(text), start + 4000)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end:
            key = m.group(2).strip()
            if key not in entries:
                entries[key] = text[start:end]

out = "/home/ubuntu/pfe/thesis/latex/Bibliography/bibliography.bib"
with open(out, "w") as f:
    f.write("% Auto-harvested from wide-research reports\n\n")
    f.write("\n\n".join(entries.values()) + "\n")
print(f"{len(entries)} unique entries -> {out}")
