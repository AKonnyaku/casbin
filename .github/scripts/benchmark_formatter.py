import pathlib, re, sys

try:
    p = pathlib.Path("comparison.md")
    if not p.exists():
        print("comparison.md not found, skipping post-processing.")
        sys.exit(0)

    lines = p.read_text(encoding="utf-8").splitlines()
    processed_lines = []
    in_code = False
    delta_col = None  # record "Diff" column start per table
    header_has_vs_base = False  # ensure benchstat header shows base/pr order

    ALIGN_COLUMN = 60  # fallback alignment when header not found

    def strip_worker_suffix(text: str) -> str:
        return re.sub(r'(\S+?)-\d+(\s|$)', r'\1\2', text)

    def get_icon(diff_val: float) -> str:
        if diff_val > 10:
            return "🐌"
        if diff_val < -10:
            return "🚀"
        return "➡️"

    def clean_superscripts(text: str) -> str:
        return re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', text)

    def parse_val(token: str):
        if '%' in token or '=' in token:
            return None
        token = clean_superscripts(token)
        token = token.split('±')[0].strip()
        token = token.split('(')[0].strip()
        if not token:
            return None

        m = re.match(r'^([-+]?\d*\.?\d+)([a-zA-Zµ]+)?$', token)
        if not m:
            return None
        try:
            val = float(m.group(1))
        except ValueError:
            return None
        suffix = (m.group(2) or "").replace("µ", "u")
        multipliers = {
            "n": 1e-9,
            "ns": 1e-9,
            "u": 1e-6,
            "us": 1e-6,
            "m": 1e-3,
            "ms": 1e-3,
            "s": 1.0,
            "k": 1e3,
            "K": 1e3,
            "M": 1e6,
            "G": 1e9,
            "Ki": 1024.0,
            "Mi": 1024.0**2,
            "Gi": 1024.0**3,
            "Ti": 1024.0**4,
            "B": 1.0,
            "B/op": 1.0,
        }
        if suffix and suffix not in multipliers:
            raise ValueError(f"Unexpected unit: {suffix}")
        return val * multipliers.get(suffix, 1.0)

    def extract_two_numbers(tokens):
        found = []
        for t in tokens[1:]:  # skip name
            if t in {"±", "∞", "~", "│", "│"}:
                continue
            if '%' in t or '=' in t:
                continue
            val = parse_val(t)
            if val is not None:
                found.append(val)
                if len(found) == 2:
                    break
        return found

    for line in lines:
        if line.strip() == "```":
            in_code = not in_code
            delta_col = None  # reset per code block
            header_has_vs_base = False
            processed_lines.append(line)
            continue

        if not in_code:
            processed_lines.append(line)
            continue

        # footnotes keep untouched
        if re.match(r'^\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]', line) or re.search(r'need\s*>?=\s*\d+\s+samples', line):
            processed_lines.append(line)
            continue

        # header lines: ensure last column labeled Diff and record its column start
        if '│' in line and ('Delta' in line or 'Diff' in line):
            if 'Delta' in line:
                line = line.replace('Delta', 'Diff', 1)
            delta_col = line.find('Diff')
            if 'vs base' in line:
                header_has_vs_base = True
            processed_lines.append(line)
            continue

        # non-data meta lines
        if not line.strip() or line.strip().startswith(('goos:', 'goarch:', 'pkg:')):
            processed_lines.append(line)
            continue

        original_line = line
        line = strip_worker_suffix(line)
        tokens = line.split()
        if not tokens:
            processed_lines.append(line)
            continue

        numbers = extract_two_numbers(tokens)
        pct_match = re.search(r'([+-]?\d+\.\d+)%', line)

        # Ensure header conveyed order; otherwise fail fast to avoid sign confusion
        if not header_has_vs_base:
            raise ValueError("benchstat header missing 'vs base' — cannot determine base/PR order.")

        # Special handling for geomean when values missing or zero
        is_geomean = tokens[0] == "geomean"
        if is_geomean and (len(numbers) < 2 or any(v == 0 for v in numbers)):
            target_col = delta_col if delta_col is not None else ALIGN_COLUMN
            leading = re.match(r'^\s*', line).group(0)
            left = f"{leading}geomean"
            if len(left) < target_col:
                left = left + " " * (target_col - len(left))
            else:
                left = left + "  "
            processed_lines.append(f"{left}n/a (has zero)")
            continue

        # when both values are zero, force diff = 0 and align
        if len(numbers) == 2 and numbers[0] == 0 and numbers[1] == 0:
            diff_val = 0.0
            icon = get_icon(diff_val)

            left = line.rstrip()
            target_col = delta_col if delta_col is not None else ALIGN_COLUMN
            if len(left) < target_col:
                left = left + " " * (target_col - len(left))
            else:
                left = left + "  "

            processed_lines.append(f"{left}{diff_val:+.2f}% {icon}")
            continue

        # recompute diff when we have two numeric values
        if len(numbers) == 2 and numbers[0] != 0:
            diff_val = (numbers[1] - numbers[0]) / numbers[0] * 100
            icon = get_icon(diff_val)

            left = line
            if pct_match:
                left = line[:pct_match.start()].rstrip()
            else:
                left = line.rstrip()

            target_col = delta_col if delta_col is not None else ALIGN_COLUMN
            if len(left) < target_col:
                left = left + " " * (target_col - len(left))
            else:
                left = left + "  "

            processed_lines.append(f"{left}{diff_val:+.2f}% {icon}")
            continue

        # fallback: align existing percentage to Diff column and (re)append icon
        if pct_match:
            try:
                pct_val = float(pct_match.group(1))
                icon = get_icon(pct_val)

                left = line[:pct_match.start()].rstrip()
                suffix = line[pct_match.end():]
                # Remove any existing icon after the percentage to avoid duplicates
                suffix = re.sub(r'\s*(🐌|🚀|➡️)', '', suffix)

                target_col = delta_col if delta_col is not None else ALIGN_COLUMN
                if len(left) < target_col:
                    left = left + " " * (target_col - len(left))
                else:
                    left = left + "  "

                processed_lines.append(f"{left}{pct_val:+.2f}% {icon}{suffix}")
            except ValueError:
                processed_lines.append(line)
            continue

        # If we cannot parse numbers or percentages, keep the original (only worker suffix stripped)
        processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")

except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
