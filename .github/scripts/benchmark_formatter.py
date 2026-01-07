import pathlib, re, sys

try:
    p = pathlib.Path("comparison.md")
    if not p.exists():
        print("comparison.md not found, skipping post-processing.")
        sys.exit(0)
        
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    in_code = False
    
    # Configuration for alignment
    ALIGN_COLUMN = 60
    
    def strip_worker_suffix(text: str) -> str:
        # Removes -8, -4 suffixes from test names
        # But be careful not to strip from non-test lines
        return re.sub(r'^(\S+?)-\d+(\s+)', r'\1\2', text)

    def get_icon(diff_val):
        if diff_val > 10: return "🐌"
        if diff_val < -10: return "🚀"
        return "➡️"

    def parse_val(s):
        # Parses benchstat numbers like "1.23k", "100ns", "0.005"
        # Returns float value or None
        # Remove statistical info
        s = s.split('±')[0].strip()
        # Remove parens
        s = s.split('(')[0].strip()
        if not s: return None
        
        # Regex for number + suffix
        m = re.match(r'^([-+]?\d*\.?\d+)([a-zA-Zµ]*)', s)
        if not m: return None
        
        try:
            val = float(m.group(1))
        except ValueError:
            return None
            
        suffix = m.group(2)
        multipliers = {
            'n': 1e-9, 'ns': 1e-9,
            'u': 1e-6, 'µ': 1e-6, 'us': 1e-6, 'µs': 1e-6,
            'm': 1e-3, 'ms': 1e-3,
            's': 1,
            'k': 1e3, 'M': 1e6, 'G': 1e9,
        }
        
        if suffix in multipliers:
            val *= multipliers[suffix]
        
        return val

    processed_lines = []
    
    for line in lines:
        if line.strip() == "```":
            in_code = not in_code
            processed_lines.append(line)
            continue
        if not in_code:
            processed_lines.append(line)
            continue
            
        # Processing inside code block
        original_line = line
        
        # 1. Identify Headers
        # Headers usually contain units or "old" / "new"
        # We want to add "Delta" to the header row that contains "vs base" or units
        if '│' in line:
            # It's a header line
            if 'Delta' not in line and ('vs base' in line or '/op' in line):
                 # Strip existing trailing whitespace
                 line = line.rstrip()
                 # Pad to ALIGN_COLUMN
                 if len(line) < ALIGN_COLUMN:
                     line = line + " " * (ALIGN_COLUMN - len(line))
                 else:
                     line = line + "   "
                 line += "Delta"
            processed_lines.append(line)
            continue
            
        # 2. Identify Data Rows (Test names or geomean)
        # Skip if it looks like a header or empty
        if not line.strip() or line.strip().startswith(('goos:', 'goarch:', 'pkg:')):
            processed_lines.append(line)
            continue

        # Try to parse columns
        # Split by multiple spaces
        parts = re.split(r'\s{2,}', line.strip())
        
        # If less than 3 parts (Name, Val1, Val2), it might not be a comparison row
        # But sometimes Name and Val1 are separated by 1 space? Benchstat aligns with spaces.
        # Let's use a more robust token extraction: find all numbers
        
        # We need to preserve the text part (Name) and then find the values.
        # Let's assume the line is: NAME <spaces> VAL1 <spaces> VAL2 ...
        
        # Find all number-like tokens
        tokens = line.split()
        if not tokens:
            processed_lines.append(line)
            continue
            
        # Check if first token is a test name or geomean
        name = tokens[0]
        is_geomean = (name == 'geomean')
        
        # Strip suffix from name in the output line if it's a test
        if not is_geomean:
            line = strip_worker_suffix(line)
            
        # Now try to find the two comparison values
        # They are usually the first two tokens that parse successfully as numbers
        # skipping the name
        
        vals = []
        val_indices = [] # tuple of (start, end) in the original line? Hard because of split
        # Just extracting values for calculation
        
        # Iterate tokens to find values
        # Skip name
        potential_val_tokens = tokens[1:]
        
        parsed_vals = []
        for t in potential_val_tokens:
            v = parse_val(t)
            if v is not None:
                parsed_vals.append(v)
                if len(parsed_vals) == 2:
                    break
        
        # If we found 2 values, calculate delta
        if len(parsed_vals) == 2:
            v1, v2 = parsed_vals
            
            # Check if there is already a percentage in the line (Benchstat output)
            # If so, we just want to decorate it, NOT append a new one
            # Benchstat delta format: -10.00% or ~
            existing_pct_match = re.search(r'([+-]?\d+\.\d+)%', line)
            existing_tilde = '~' in line.split()[-1] if line.split() else False # Loose check for ~
            
            diff = 0.0
            if v1 != 0:
                diff = (v2 - v1) / v1 * 100
                
            icon = get_icon(diff)
            
            if existing_pct_match:
                # Insert icon after percentage
                # We want to align this column too?
                # The user complained about alignment.
                # Let's reconstruct the line end.
                
                # Find where the percentage ends
                end_idx = existing_pct_match.end()
                
                # If we just insert, alignment might shift.
                # But benchstat output is already aligned.
                # Just appending the icon might be enough if it's the last thing.
                # But user wants "Delta" header aligned.
                
                # Let's try to force the percentage to be at ALIGN_COLUMN
                
                # Cut the line before the percentage
                start_idx = existing_pct_match.start()
                prefix = line[:start_idx].rstrip()
                pct_str = existing_pct_match.group(0)
                suffix = line[end_idx:] # (p=0.000 n=10) etc.
                
                # Reconstruct
                # Pad prefix
                if len(prefix) < ALIGN_COLUMN:
                    prefix = prefix + " " * (ALIGN_COLUMN - len(prefix))
                else:
                    prefix = prefix + "   "
                    
                new_line = f"{prefix}{pct_str} {icon}{suffix}"
                processed_lines.append(new_line)
                
            elif existing_tilde:
                 # It's statistically insignificant
                 # Find the tilde
                 # Usually it's a standalone token "~"
                 # We can replace "~" with "~ ➡️" and align it?
                 
                 # Regex for standalone tilde
                 tilde_match = re.search(r'\s~\s', line)
                 if not tilde_match:
                     tilde_match = re.search(r'\s~', line) # End of line
                     
                 if tilde_match:
                     start_idx = tilde_match.start()
                     prefix = line[:start_idx].rstrip()
                     suffix = line[tilde_match.end():]
                     
                     if len(prefix) < ALIGN_COLUMN:
                        prefix = prefix + " " * (ALIGN_COLUMN - len(prefix))
                     else:
                        prefix = prefix + "   "
                        
                     new_line = f"{prefix} ~ ➡️{suffix}"
                     processed_lines.append(new_line)
                 else:
                     processed_lines.append(line)

            else:
                # No existing delta found (e.g. allocs/op might not have it if counts are same? Or benchstat didn't output it)
                # Append our calculated delta
                
                # If v1 == v2 (diff == 0), benchstat might show nothing or ~?
                # If we calculated it, append it.
                
                line = line.rstrip()
                if len(line) < ALIGN_COLUMN:
                    line = line + " " * (ALIGN_COLUMN - len(line))
                else:
                    line = line + "   "
                    
                new_line = f"{line}{diff:+.2f}% {icon}"
                processed_lines.append(new_line)
        else:
            # Couldn't parse 2 values, just print line
            processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
