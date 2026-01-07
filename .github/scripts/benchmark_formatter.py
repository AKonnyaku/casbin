
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
            
        # Processing inside code block
        
        # 1. Identify Headers STRICTLY
        # Headers must contain specific keywords
        is_header = False
        if '│' in line:
            if 'old.txt' in line or 'new.txt' in line or 'vs base' in line or '/op' in line:
                is_header = True
        
        if is_header:
            if 'Delta' not in line and ('vs base' in line or '/op' in line):
                 line = line.rstrip()
                 # Try to align Delta header nicely
                 if len(line) < ALIGN_COLUMN:
                     line = line + " " * (ALIGN_COLUMN - len(line))
                 else:
                     line = line + "   "
                 line += "Delta"
            processed_lines.append(line)
            continue
            
        # 2. Identify Data Rows
        if not line.strip() or line.strip().startswith(('goos:', 'goarch:', 'pkg:')):
            processed_lines.append(line)
            continue

        # Try to parse columns
        # Treat '│' as a delimiter that we might need to skip or handle
        # But parse_val will handle it (return None)
        
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
                # Align based on the percentage position
                start_idx = existing_pct_match.start()
                prefix = line[:start_idx].rstrip()
                pct_str = existing_pct_match.group(0)
                suffix = line[existing_pct_match.end():]
                
                if len(prefix) < ALIGN_COLUMN:
                    prefix = prefix + " " * (ALIGN_COLUMN - len(prefix))
                else:
                    prefix = prefix + "   "
                    
                new_line = f"{prefix}{pct_str} {icon}{suffix}"
                processed_lines.append(new_line)
                
            elif existing_tilde:
                 # Find the tilde
                 tilde_match = re.search(r'\s~\s', line)
                 if not tilde_match:
                     tilde_match = re.search(r'\s~', line) # End of line or before pipe
                     
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
                     # Fallback if tilde regex fails
                     processed_lines.append(line)

            else:
                # No percentage, no tilde. Append our own.
                line = line.rstrip()
                # If there is a trailing pipe '│', we should probably insert BEFORE it?
                # But benchstat output with pipes usually has values inside.
                # If we are here, it means no percentage was found.
                
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
            # Couldn't parse 2 values
            processed_lines.append(line)

    p.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    
except Exception as e:
    print(f"Error post-processing comparison.md: {e}")
    sys.exit(1)
