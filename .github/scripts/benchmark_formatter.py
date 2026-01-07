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
    
    def clean_superscripts(text: str) -> str:
        # Removes superscript characters that might interfere with number parsing
        return re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', text)

    def strip_worker_suffix(text: str) -> str:
        # Removes -8, -4 suffixes from test names
        # Copilot recommendation: remove ^ anchor and allow end of string match
        return re.sub(r'(\S+?)-\d+(\s|$)', r'\1\2', text)

    def get_icon(diff_val):
        if diff_val > 10: return "🐌"
        if diff_val < -10: return "🚀"
        return "➡️"

    def parse_val(s):
        # Parses benchstat numbers like "1.23k", "100ns", "0.005"
        # Returns float value or None
        
        if '%' in s or '=' in s:
            return None
            
        s = clean_superscripts(s)
        s = s.split('±')[0].strip()
        s = s.split('(')[0].strip()
        if not s: return None
        
        # Regex for number + suffix
        # Handle cases like "100" (no suffix) or "100B" (B suffix)
        m = re.match(r'^([-+]?\d*\.?\d+)([a-zA-Zµ]*)$', s)
        if not m: return None
        
        try:
            val = float(m.group(1))
        except ValueError:
            return None
            
        suffix = m.group(2)
        # Handle 'u' vs 'µ' normalization
        if suffix == 'µ': suffix = 'u'
        if suffix == 'µs': suffix = 'us'
        
        multipliers = {
            'n': 1e-9, 'ns': 1e-9,
            'u': 1e-6, 'us': 1e-6,
            'm': 1e-3, 'ms': 1e-3,
            's': 1.0,
            'k': 1e3, 'K': 1e3, 
            'M': 1e6, 
            'G': 1e9,
            'Ki': 1024.0, 'Mi': 1024.0**2, 'Gi': 1024.0**3, 'Ti': 1024.0**4,
            'B': 1.0, 'B/op': 1.0,
            '': 1.0, # No unit
        }
        
        # Copilot recommendation: Strict unit handling
        if suffix not in multipliers:
            return None
            
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

        # Skip footnote lines
        if re.match(r'^\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]', line) or re.search(r'need\s*>?=\s*\d+\s+samples', line):
            processed_lines.append(line)
            continue
            
        # Processing inside code block
        
        # 1. Identify Headers STRICTLY
        # Headers must contain specific keywords
        is_header = False
        if '│' in line:
            if 'old.txt' in line or 'new.txt' in line or 'vs base' in line or '/op' in line:
                is_header = True
        
        if is_header:
            if 'Delta' not in line and 'vs base' in line:
                line = re.sub(r'(vs base)(\s*)', r'\1  Delta\2', line, count=1)
            processed_lines.append(line)
            continue
            
        # 2. Identify Data Rows
        if not line.strip() or line.strip().startswith(('goos:', 'goarch:', 'pkg:')):
            processed_lines.append(line)
            continue

        # Try to parse columns
        tokens = line.split()
        if not tokens:
            processed_lines.append(line)
            continue
            
        name = tokens[0]
        # Skip pipe if it's the first token
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
            # Use strict regex to avoid matching inside other words
            existing_pct_match = re.search(r'([+-]?\d+\.\d+)%', line)
            
            # Check for tilde indicating insignificant difference
            existing_tilde = False
            # Look for " ~ " surrounded by spaces, or at ends
            if re.search(r'(^|\s)~(\s|$)', line):
                existing_tilde = True
            
            if existing_pct_match:
                # If icon already exists, don't add another
                if re.search(r'(🐌|🚀|➡️)', line):
                    processed_lines.append(line)
                else:
                    end_idx = existing_pct_match.end()
                    # Insert icon after the percentage
                    processed_lines.append(f"{line[:end_idx]} {icon}{line[end_idx:]}")
                
            elif existing_tilde:
                 if re.search(r'(🐌|🚀|➡️)', line):
                     processed_lines.append(line)
                 else:
                     # Find the tilde and append arrow
                     # We want to replace "~" with "~ ➡️" or just append it? 
                     # Usually benchstat output: "0.10n ± 1%  0.10n ± 1%  ~ (p=0.999)"
                     # We just want to ensure the arrow is there.
                     processed_lines.append(line.replace("~", "~ ➡️", 1))

            else:
                # No percentage, no tilde. Append our own.
                line = line.rstrip()
                
                # Check for trailing pipe
                if line.endswith('│'):
                    line = line[:-1].rstrip()
                    suffix = " │"
                else:
                    suffix = ""
                
                # Force alignment
                if len(line) < ALIGN_COLUMN:
                    line = line + " " * (ALIGN_COLUMN - len(line))
                else:
                    line = line + "   "
                    
                new_line = f"{line}{diff:+.2f}% {icon}{suffix}"
                processed_lines.append(new_line)
        else:
            # Couldn't parse 2 values
            if is_geomean:
                # Handle geomean with missing values (e.g. zeros)
                # Check for percentage
                pct_match = re.search(r'([+-]?\d+\.\d+)%', line)
                if pct_match:
                    diff_str = pct_match.group(1) + "%"
                    try:
                        diff_val = float(pct_match.group(1))
                        icon = get_icon(diff_val)
                    except ValueError:
                        icon = "➡️"
                    
                    left_part = "geomean       n/a (has zero)"
                    
                    # Align
                    if len(left_part) < ALIGN_COLUMN:
                        left_part += " " * (ALIGN_COLUMN - len(left_part))
                    else:
                        left_part += "   "
                    
                    # Check for trailing pipe in original line
                    suffix = ""
                    if line.rstrip().endswith('│'):
                        suffix = " │"
                        
                    processed_lines.append(f"{left_part}{diff_str} {icon}{suffix}")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
