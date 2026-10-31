import re, sys, json
PO = "/home/claude/bambulab/bambustudio/bbl/i18n/de/BambuStudio_de.po"

def parse(path):
    entries = []
    cur = {"ctx": None, "id": "", "str": "", "state": None}
    def flush():
        nonlocal cur
        if cur["id"] != "" or cur["str"] != "":
            entries.append(cur)
        cur = {"ctx": None, "id": "", "str": "", "state": None}
    def unq(s):
        s = s.strip()
        assert s.startswith('"') and s.endswith('"'), s
        return bytes(s[1:-1], "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") if False else s[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                continue
            if line.strip() == "":
                flush(); continue
            if line.startswith("msgctxt"):
                if cur["id"] or cur["str"]:
                    flush()
                cur["ctx"] = unq(line[len("msgctxt"):]); cur["state"] = "ctx"
            elif line.startswith("msgid_plural"):
                cur["state"] = "plural"
            elif line.startswith("msgid"):
                if cur["str"]:
                    flush()
                cur["id"] = unq(line[len("msgid"):]); cur["state"] = "id"
            elif line.startswith("msgstr"):
                cur["str"] = unq(line[line.index('"'):]) if '"' in line else ""; cur["state"] = "str"
            elif line.startswith('"'):
                t = unq(line)
                if cur["state"] == "id": cur["id"] += t
                elif cur["state"] == "str": cur["str"] += t
                elif cur["state"] == "ctx": cur["ctx"] += t
    flush()
    return entries

if __name__ == "__main__":
    E = parse(PO)
    print(len(E), "Eintraege", file=sys.stderr)
    exact = {}
    for e in E:
        exact.setdefault(e["id"], []).append(e)
    for q in sys.argv[1:]:
        if q.startswith("~"):
            sub = q[1:].lower()
            hits = [e for e in E if sub in e["id"].lower()]
            print(f"## ~{sub}: {len(hits)} Treffer")
            for e in hits[:25]:
                print(f"  [{e['ctx']}] {e['id'][:90]!r} -> {e['str'][:110]!r}")
        else:
            hits = exact.get(q, [])
            if not hits:
                print(f"## {q!r}: --- nicht vorhanden ---")
            for e in hits:
                print(f"## {q!r} [{e['ctx']}] -> {e['str']!r}")
