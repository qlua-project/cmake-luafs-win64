import re
import subprocess
from pathlib import Path
from collections import defaultdict

# Configuration
git_root_str = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], 
    encoding='utf-8'
).strip()

DUMP_DIR = Path(__file__).resolve().parent.relative_to(git_root_str)
FILES_DUMPBIN = [
    "lfs.dll.dependents.txt",
    "lfs.dll.exports.txt", 
    "lfs.dll.headers.txt",
    "lfs.dll.imports.txt"
]
FILE_LDD = "lfs.dll.ldd.txt"

def get_git_content(fpath):
    """Retrieves file content from the last git commit via subprocess."""
    try:
        git_path = str(fpath).replace("\\", "/")
        return subprocess.check_output(
            ["git", "show", f"HEAD:{git_path}"], 
            text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return None

def get_fuzzy_key(line):
    """
    Generates a comparison key by stripping hex, addresses, and timestamps.
    Keeps the labels (e.g., 'time date stamp') so lines align in git diff.
    """
    if not line.strip(): 
        return ""
    # 1. Handle Timestamps: Keep the label but strip the varying date/time part
    if "time date stamp" in line.lower():
        return "timedatestamp"
    # 2. General Hex/Address stripping
    # Remove hex 0x..., (range to range), and raw 4/16 char hex strings
    line = re.sub(r'0x[0-9a-fA-F]+', '', line)
    line = re.sub(r'\([0-9a-fA-F\s]+to[0-9a-fA-F\s]+\)', '', line)
    line = re.sub(r'\b[0-9a-fA-F]{1,16}\b', '', line)
    return "".join(line.split())

def get_indent(line):
    """Returns the number of leading spaces in a string."""
    return len(line) - len(line.lstrip(' '))

def parse_blocks(text):
    """Parses text into a list of tuples: (starting_line_index, [content_lines])."""
    lines = text.splitlines()
    blocks = []
    current_block = []
    start_idx = 0
    
    for i, line in enumerate(lines):
        # 1. If line is blank, check if we should end the block
        if not line.strip():
            # Peek at the NEXT line to see if it starts with a digit
            next_idx = i + 1
            if next_idx < len(lines):
                next_line = lines[next_idx]
                 # Condition A: Starts with a digit
                starts_with_digit = next_line.strip()[:1].isdigit()
                # Condition B: Indentation is deeper than the last line in block
                is_deeper_indent = current_block and get_indent(next_line) > get_indent(current_block[-1])
                if starts_with_digit or is_deeper_indent:
                    # Continue current block: Add the empty line to maintain spacing
                    if current_block:
                        current_block.append(line)
                        continue
            
            # Normal break: Save the current block and reset
            if current_block:
                blocks.append((start_idx, current_block))
                current_block = []
            # Prevent leading blank lines in blocks
            continue
            
        # 2. Start a new block if we aren't currently in one
        if not current_block:
            start_idx = i
        current_block.append(line)
        
    # 3. Catch the final block
    if current_block:
        blocks.append((start_idx, current_block))
    return blocks

def align_and_save(filename):
    """Reorders working copy lines/blocks to match Git anchor positions."""
    fpath = DUMP_DIR / filename
    if not fpath.exists():
        return
    
    working_text = fpath.read_text(encoding='utf-8', errors='ignore')
    git_text = get_git_content(fpath)
    
    # If no anchor (git version), do nothing to the working copy
    if not git_text:
        print(f"  [Skip] No Git anchor for {filename}")
        return

    # Use first line of block as key:
    # { fuzzy_header_key : (git_start_line, [original_git_lines]) }
    git_blocks = parse_blocks(git_text)
    git_map = {b[1][0]: b for b in git_blocks if b[1]}  # get_fuzzy_key(b[1][0])

    work_blocks = parse_blocks(working_text)

    # Prepare a canvas to place blocks at specific line indices
    git_lines_raw = git_text.splitlines()
    # Define a safe maximum canvas size
    max_lines = max(len(git_lines_raw), len(working_text.splitlines())) * 2
    # Spatial Alignment Canvas
    canvas = [None] * max_lines
    unplaced_blocks = []
    
    # Professional 'Infinity' sentinel for sorting new items to the end
    SORT_TO_END = float('inf')
    
    for _, w_lines in work_blocks:
        header_key = w_lines[0]  # get_fuzzy_key(w_lines[0])
        
        # Track duplicates for warnings
        seen_fuzzy_counts = defaultdict(int)
        for ln in w_lines:
            fk = get_fuzzy_key(ln)
            if fk:
                seen_fuzzy_counts[fk] += 1
                if seen_fuzzy_counts[fk] > 1:
                    print(f"  [Warning] Duplicate in {filename}: {ln.strip()[:40]}...")
        
        if header_key in git_map:
            git_start_idx, g_lines = git_map[header_key]
            
            # Map fuzzy keys to a list of original indices for positional matching
            g_positions = defaultdict(list)
            for idx, gl in enumerate(g_lines):
                g_positions[get_fuzzy_key(gl)].append(idx)
            
            # Create a list of tuples: (target_index, original_line)
            # This aligns the N-th occurrence in 'Work' to the N-th occurrence in 'Git'
            indexed_w_lines = []
            for ln in w_lines:
                fk = get_fuzzy_key(ln)
                # If fuzzy match exists in Git, take the earliest available index
                if fk in g_positions and g_positions[fk]:
                    target_idx = g_positions[fk].pop(0) # Consume the first available Git index
                else:
                    target_idx = SORT_TO_END # New line or extra duplicate: send to end of block
                indexed_w_lines.append((target_idx, ln))
            
            # Sort lines based on the consumed Git indices
            #   Note: Items with float('inf') maintain their relative order 
            #   because Python's sort() is stable.
            indexed_w_lines.sort(key=lambda x: x[0])
            # Extract just the lines after sorting
            aligned_block = [item[1] for item in indexed_w_lines]
            
            # Place block at the exact historical Git line index
            canvas[git_start_idx : git_start_idx + len(aligned_block)] = aligned_block
        else:
            unplaced_blocks.append(w_lines)

    # Reconstruct final file structure
    output = []
    for i in range(max_lines):
        if canvas[i] is not None:
            output.append(canvas[i])
        elif i < len(git_lines_raw) and not git_lines_raw[i].strip():
            output.append("") # Preserve original empty line structure
            
    # Append completely new blocks (those not found in git) to the end
    for b in unplaced_blocks:
        if output and output[-1] != "":
            output.append("")
        output.extend(b)

    # Save to disk with final rstrip to avoid trailing blank blocks
    fpath.write_text("\n".join(output).rstrip() + "\n", encoding='utf-8')
    print(f"  [Done] Aligned {filename}")

def process_files():
    """Main execution loop for all tracked files."""
    print(f"Aligning working copy in {DUMP_DIR} with Git HEAD...")
    
    for fname in FILES_DUMPBIN:
        align_and_save(fname)
        
    # LDD handling
    align_and_save(FILE_LDD)

if __name__ == "__main__":
    process_files()
