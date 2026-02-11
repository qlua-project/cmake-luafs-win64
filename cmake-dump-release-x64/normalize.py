import re
import subprocess
from pathlib import Path

# Configuration
DUMP_DIR = Path("./cmake-dump-release-x64")
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
    # Remove hex 0x..., (range to range), and raw 8/16 char hex strings
    line = re.sub(r'0x[0-9a-fA-F]+', '', line)
    line = re.sub(r'\([0-9a-fA-F\s]+to[0-9a-fA-F\s]+\)', '', line)
    line = re.sub(r'\b[0-9a-fA-F]{8,16}\b', '', line)
    return "".join(line.split())

def parse_blocks(text):
    """Parses text into a list of tuples: (starting_line_index, [content_lines])."""
    lines = text.splitlines()
    blocks = []
    current_block = []
    start_idx = 0
    
    for i, line in enumerate(lines):
        if not line.strip():
            if current_block:
                blocks.append((start_idx, current_block))
                current_block = []
            continue
        if not current_block:
            start_idx = i
        current_block.append(line)
        
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
    
    # If no anchor (git version), do nothing as requested
    if not git_text:
        print(f"  [Skip] No Git anchor for {filename}")
        return

    # Map Git Blocks: { fuzzy_header_key : (git_start_line, [original_git_lines]) }
    git_blocks = parse_blocks(git_text)
    git_map = {get_fuzzy_key(b[1][0]): b for b in git_blocks if b[1]}

    work_blocks = parse_blocks(working_text)
    
    # Prepare a canvas to place blocks at specific line indices
    git_lines_raw = git_text.splitlines()
    max_lines = max(len(git_lines_raw), len(working_text.splitlines())) * 2
    canvas = [None] * max_lines
    unplaced_blocks = []

    for _, w_lines in work_blocks:
        header_key = get_fuzzy_key(w_lines[0])
        
        # Check for duplicates in working copy block
        seen_fuzzy = {}
        for ln in w_lines:
            fk = get_fuzzy_key(ln)
            if fk in seen_fuzzy:
                print(f"  [Warning] Duplicate in {filename}: {ln.strip()[:50]}...")
            seen_fuzzy[fk] = ln

        if header_key in git_map:
            git_start_idx, g_lines = git_map[header_key]
            
            # Reorder internal lines using Git sequence as anchor
            g_order = {get_fuzzy_key(gl): idx for idx, gl in enumerate(g_lines)}
            aligned_block = sorted(w_lines, key=lambda l: g_order.get(get_fuzzy_key(l), 999))
            
            # Place block at the exact historical Git line index
            canvas[git_start_idx : git_start_idx + len(aligned_block)] = aligned_block
        else:
            unplaced_blocks.append(w_lines)

    # Reconstruct final file
    output = []
    for i in range(max_lines):
        if canvas[i] is not None:
            output.append(canvas[i])
        elif i < len(git_lines_raw) and not git_lines_raw[i].strip():
            output.append("") # Preserve original empty line structure
            
    # Append completely new blocks at the end
    for b in unplaced_blocks:
        if output and output[-1] != "":
            output.append("")
        output.extend(b)

    fpath.write_text("\n".join(output).rstrip() + "\n", encoding='utf-8')
    print(f"  [Done] Aligned {filename}")

def process_files():
    """Main execution loop for all tracked files."""
    print(f"Aligning working copy in {DUMP_DIR} with Git HEAD...")
    
    for fname in FILES_DUMPBIN:
        align_and_save(fname)
        
    # LDD handling (simpler, usually one block)
    align_and_save(FILE_LDD)

if __name__ == "__main__":
    process_files()
