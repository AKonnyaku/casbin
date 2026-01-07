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
        # Removes -8, -4 suffixes from test names
        return re.sub(r'(\S+?)-\d+(\s|$)', r'\1\2', text)

    def get_icon(diff_val):
        if diff_val > 10: return "🐌"
        if diff_val < -10: return "🚀"
        return "➡️"

    def decorate(line: str) -> str:
        original_line = line
        line = strip_worker_suffix(line)

        # Handle Header Rows
        # Benchstat headers often look like: │ sec/op │ sec/op vs base │
        if '│' in line and ('sec/op' in line or 'B/op' in line or 'allocs/op' in line):
             if 'Delta' not in line and 'vs base' in line:
                 # Align Delta header with the data column we are about to add
                 return line + "   Delta"
             return line

        # 1. Existing percentage (from benchstat)
        # Matches: -10.00% or +5.5%
        m = re.search(r'([+-]?\d+\.\d+)%', line)
        if m:
            diff = float(m.group(1))
            icon = get_icon(diff)
            # Insert icon after the percentage
            return line[:m.end()] + " " + icon + line[m.end():]

        # 2. Calculate from values if percentage is missing
        # We need to support time (ns, µs, ms, s), bytes (B), and counts (allocs)
        # Regex to capture number and unit. 
        # Units: n, µ, u, m, s (time); B (bytes); (empty) for allocs if strictly number? 
        # Actually allocs/op usually appears as just a number in benchstat output if the unit is implicit,
        # but benchstat usually puts the unit in the header.
        # Let's try to capture generic numbers.
        
        # Strategy: Look for two distinct numbers that look like benchmark results.
        # Benchstat lines: Name  Val1 Unit  Val2 Unit ...
        # Or: Name Val1 Val2 ...
        
        # Let's try to match based on the known columns structure from user description
        # But since we don't have the exact file content, we rely on patterns.
        
        # Match time units: 10.5µ
        time_matches = re.findall(r'(\d+(?:\.\d+)?)([nµmsu])', line)
        if len(time_matches) >= 2:
            def parse_time(num_str, unit_str):
                v = float(num_str)
                if unit_str == 'n': return v * 1e-9
                if unit_str in ['µ', 'u']: return v * 1e-6
                if unit_str == 'm': return v * 1e-3
                if unit_str == 's': return v
                return v
            
            v1 = parse_time(time_matches[0][0], time_matches[0][1])
            v2 = parse_time(time_matches[1][0], time_matches[1][1])
            
            if v1 != 0:
                diff = (v2 - v1) / v1 * 100
                icon = get_icon(diff)
                # Use a fixed width or tab to align. Tab might be safer for simple display.
                return f"{line:<60} {diff:+.2f}% {icon}"

        # Match Byte units: 1024B
        byte_matches = re.findall(r'(\d+(?:\.\d+)?)B\b', line)
        if len(byte_matches) >= 2:
            v1 = float(byte_matches[0])
            v2 = float(byte_matches[1])
            if v1 != 0:
                diff = (v2 - v1) / v1 * 100
                icon = get_icon(diff)
                return f"{line:<60} {diff:+.2f}% {icon}"

        # Match Allocations (just numbers, usually integers, often followed by spaces)
        # This is risky as it might match test names containing numbers.
        # However, benchmark rows usually start with a name.
        # Let's rely on the fact that if we didn't match time or bytes, and it looks like a data row.
        # Data rows typically don't start with 'goos', 'goarch', 'pkg', etc.
        if not any(line.strip().startswith(p) for p in ['goos:', 'goarch:', 'pkg:', '│']):
            # Try to find last two numbers
            # Assuming format: Name ... Val1 ... Val2
            nums = re.findall(r'\b(\d+)\b', line)
            # Filter out numbers that are likely part of the name (start of line)
            # This is heuristic.
            # Better approach: check if the line contains 'allocs/op' in header context? No, we are processing line by line.
            
            # If we assume standard benchstat 2-column output:
            # Name Val1 Val2
            if len(nums) >= 2:
                 # Take the last two numbers
                v1 = float(nums[-2])
                v2 = float(nums[-1])
                # Only if they are reasonably close or it's clearly data?
                # Let's strict it to lines that likely don't have units attached (allocs)
                # and are not time/byte lines processed above.
                if 'allocs/op' in '\n'.join(lines): # Check global context if possible, but expensive inside loop
                    pass

                # If the line ends with a number, it's likely allocs or bytes without unit suffix
                if re.search(r'\d+$', line.strip()):
                     if v1 != 0:
                        diff = (v2 - v1) / v1 * 100
                        icon = get_icon(diff)
                        return f"{line:<60} {diff:+.2f}% {icon}"

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
