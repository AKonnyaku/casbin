import pathlib, re, sys

try:
    p = pathlib.Path("comparison.md")
    if not p.exists():
        print("comparison.md not found, skipping post-processing.")
        sys.exit(0)
        
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    in_code = False

    def strip_worker_suffix(text: str) -> str:
        return re.sub(r'(\S+?)-\d+(\s|$)', r'\1\2', text)

    def decorate(line: str) -> str:
        line = strip_worker_suffix(line)

        def get_icon(diff_val):
            if diff_val > 10: return "🐌"
            if diff_val < -10: return "🚀"
            return "➡️"

        # 1. Existing percentage
        m = re.search(r'([+-]?\d+\.\d+)%', line)
        if m:
            diff = float(m.group(1))
            icon = get_icon(diff)
            return line[:m.end()] + " " + icon + line[m.end():]

        # 2. Calculate from values
        matches = re.findall(r'(\d+(?:\.\d+)?)([nµmsu])', line)
        if len(matches) >= 2:
            def parse_val(num_str, unit_str):
                v = float(num_str)
                if unit_str == 'n': return v * 1e-9
                if unit_str in ['µ', 'u']: return v * 1e-6
                if unit_str == 'm': return v * 1e-3
                if unit_str == 's': return v
                raise ValueError(f"Unexpected time unit: {unit_str}")

            v1 = parse_val(matches[0][0], matches[0][1])
            v2 = parse_val(matches[1][0], matches[1][1])

            if v1 != 0:
                diff = (v2 - v1) / v1 * 100
                icon = get_icon(diff)
                return f"{line}\t{diff:+.2f}% {icon}"

        return line

    for line in lines:
        if line.strip() == "```":
            in_code = not in_code
            out.append(line)
            continue
        if not in_code:
            out.append(line)
            continue
        out.append(decorate(line))

    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
