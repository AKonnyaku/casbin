
import pathlib, re, sys

try:
    p = pathlib.Path("comparison.md")
    if not p.exists():
        print("comparison.md not found, skipping post-processing.")
        sys.exit(0)
        
    lines = p.read_text(encoding="utf-8").splitlines()
    processed_lines = []
    in_code = False
    
    # Configuration for alignment
    ALIGN_COLUMN = 60
    
    def strip_worker_suffix(text: str) -> str:
        # Removes -8, -4 suffixes from test names
        return re.sub(r'^(\S+?)-\d+(\s+)', r'\1\2', text)

    def get_icon(diff_val):
        if diff_val > 10: return "🐌"
        if diff_val < -10: return "🚀"
        return "➡️"

    def parse_val(s):
        # Parses benchstat numbers like "1.23k", "100ns", "0.005"
        # Returns float value or None
        s = s.split('±')[0].strip()
        s = s.split('(')[0].strip()
        if not s: return None
        
        # Regex for number + suffix
        # STRICTLY match ASCII digits only [0-9] to avoid matching '⁴' etc.
        # \d in Python 3 matches unicode digits, so we use [0-9]
        m = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-zA-Zµ]*)', s)
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
            'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3,
            # B is bytes, count as 1 unit
            'B': 1, 
        }
        
        if suffix in multipliers:
            val *= multipliers[suffix]
        
        return val

    for line in lines:
        if line.strip() == "```":
            in_code = not in_code
            processed_lines.append(line)
            continue
        if not in_code:
            processed_lines.append(line)
            continue
            
        # Processing inside code block
        
        # SKIP Footnotes
        # Lines starting with superscript numbers ¹²³⁴
        # Or lines containing "need >= X samples"
        if re.match(r'^\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]', line):
            processed_lines.append(line)
            continue
            
        # 1. Identify Headers STRICTLY
        # Headers must contain specific keywords
        is_header = False
        if '│' in line:
            if 'old.txt' in line or 'new.txt' in line or 'vs base' in line or '/op' in line:
                is_header = True
        
        if is_header:
            if 'Delta' not in line and 'vs base' in line:
                 # Attempt to insert Delta column header nicely
                 # We want to align it with the data columns if possible
                 # But benchstat headers are usually aligned by spaces
                 line = line.rstrip()
                 # Simply append Delta at the end for now, or pad
                 if len(line) < ALIGN_COLUMN:
                     line = line + " " * (ALIGN_COLUMN - len(line))
                 else:
                     line = line + "   "
                 line += "Delta"
            processed_lines.append(line)
            continue
            
        # 2. Identify Data Rows
        if not line.strip() or line.strip().startswith(('goos:', 'goarch:', 'pkg:', 'cpu:')):
            processed_lines.append(line)
            continue

        # Try to parse columns
        tokens = line.split()
        if not tokens:
            processed_lines.append(line)
            continue
            
        name = tokens[0]
        # Skip pipe if it's the first token (unlikely but possible)
        if name == '│': 
            name = tokens[1] if len(tokens) > 1 else ''
            
        is_geomean = (name == 'geomean')
        
        if not is_geomean:
            line = strip_worker_suffix(line)
            
        # Extract values
        parsed_vals = []
        
        # We look for the first two valid numbers
        for t in tokens:
            # Skip the name itself (first token)
            if t == tokens[0]: continue
            
            v = parse_val(t)
            if v is not None:
                parsed_vals.append(v)
                if len(parsed_vals) == 2:
                    break
        
        if len(parsed_vals) == 2:
            v1, v2 = parsed_vals
            
            diff = 0.0
            if v1 != 0:
                diff = (v2 - v1) / v1 * 100
            
            icon = get_icon(diff)
            
            # Check for existing percentage or tilde
            existing_pct_match = re.search(r'([+-]?\d+\.\d+)%', line)
            existing_tilde = '~' in line.split()[-1] if line.split() else False
            
            if existing_pct_match:
                # Check if icon already exists to avoid duplication
                if re.search(r'(🐌|🚀|➡️)', line):
                    processed_lines.append(line)
                else:
                    # In-place insertion: append icon after the percentage
                    # This preserves original alignment from benchstat
                    end_idx = existing_pct_match.end()
                    processed_lines.append(f"{line[:end_idx]} {icon}{line[end_idx:]}")
                
            elif existing_tilde:
                 if re.search(r'(🐌|🚀|➡️)', line):
                     processed_lines.append(line)
                     continue
                 # Find the tilde
                 tilde_match = re.search(r'\s~\s', line)
                 if not tilde_match:
                     tilde_match = re.search(r'\s~', line) # End of line or before pipe
                     
                 if tilde_match:
                     # In-place insertion: append icon after tilde
                     end_idx = tilde_match.end()
                     processed_lines.append(f"{line[:end_idx]} ➡️{line[end_idx:]}")
                 else:
                     # Fallback if tilde regex fails
                     processed_lines.append(line)

            else:
                # No percentage, no tilde. Append our own.
                line = line.rstrip()
                
                # Check for trailing pipe
                suffix = ""
                if line.endswith('│'):
                    line = line[:-1].rstrip()
                    suffix = " │"
                
                # Use strict alignment only when appending NEW column
                if len(line) < ALIGN_COLUMN:
                    line = line + " " * (ALIGN_COLUMN - len(line))
                else:
                    line = line + "   "
                    
                new_line = f"{line}{diff:+.2f}% {icon}{suffix}"
                processed_lines.append(new_line)
        else:
            # Couldn't parse 2 values
            # This handles cases like "geomean ⁴ ⁴" where values are missing
            processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
