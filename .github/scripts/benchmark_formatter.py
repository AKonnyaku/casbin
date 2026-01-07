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
        # Matches "Name-8 " -> "Name "
        return re.sub(r'(\S+?)-\d+(\s|$)', r'\1\2', text)

    def get_icon(diff_val):
        if diff_val > 10: return "🐌"
        if diff_val < -10: return "🚀"
        return "➡️"

    def clean_superscripts(text):
        return re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', text)

    def parse_val(s):
        # Parses benchstat numbers like "1.23k", "100ns", "0.005"
        # Returns float value or None
        if '%' in s: return None
        
        s = clean_superscripts(s)
        s = s.split('±')[0].strip()
        s = s.split('(')[0].strip()
        if not s: return None
        
        # Regex for number + suffix
        # Handle cases like "100" (no suffix) or "100B" (B suffix)
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

        # Skip footnote lines and "need samples" lines
        # Check for footnote markers at start of line
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
        vals = []
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
                if re.search(r'(🐌|🚀|➡️)', line):
                    processed_lines.append(line)
                else:
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
                     processed_lines.append(f"{line[:tilde_match.end()]} ➡️{line[tilde_match.end():]}")
                 else:
                     # Fallback if tilde regex fails
                     processed_lines.append(line)

            else:
                # No percentage, no tilde. Append our own.
                line = line.rstrip()
                
                # Check for trailing pipe
                if line.endswith('│'):
                    line = line[:-1].rstrip()
                    suffix = " │"
                else:
                    suffix = ""
                
                if len(line) < ALIGN_COLUMN:
                    line = line + " " * (ALIGN_COLUMN - len(line))
                else:
                    line = line + "   "
                    
                new_line = f"{line}{diff:+.2f}% {icon}{suffix}"
                processed_lines.append(new_line)
        else:
            # Couldn't parse 2 values.
            # But maybe there is a percentage already (e.g. geomean with missing values)
            existing_pct_match = re.search(r'([+-]?\d+\.\d+)%', line)
            if existing_pct_match:
                # Check if icon already exists
                if not re.search(r'(🐌|🚀|➡️)', line):
                    # We can't calculate diff, but we can append icon based on parsed percentage?
                    # Parse the percentage string to get diff value
                    try:
                        pct_val = float(existing_pct_match.group(1))
                        icon = get_icon(pct_val)
                        end_idx = existing_pct_match.end()
                        processed_lines.append(f"{line[:end_idx]} {icon}{line[end_idx:]}")
                    except ValueError:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
