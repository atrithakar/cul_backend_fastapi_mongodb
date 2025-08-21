from pathlib import Path

# Define which file extensions you want to normalize
TEXT_EXTS = {
    ".c", ".cpp", ".h", ".hpp",
    ".py", ".txt", ".md", ".json", ".yaml", ".yml",
    ".xml", ".csv", ".html", ".css", ".js",
    ".sh", ".bat", ".ini", ".cfg",
}

def normalize_line_endings(file_path: str):
    """
    Normalize CRLF and CR to LF for allowed text extensions only.
    Skips all other files (binaries, unknown extensions).
    Returns True if the file was modified, False otherwise.
    """
    p = Path(file_path)

    if p.suffix.lower() not in TEXT_EXTS:
        # Not in whitelist → skip
        return

    try:
        raw = p.read_bytes()
    except Exception as e:
        print(f"[normalize] could not read {file_path}: {e}")
        return

    if not raw:
        return

    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    if normalized != raw:
        try:
            p.write_bytes(normalized)
            print(f"[normalize] normalized {file_path}")
            return
        except Exception as e:
            print(f"[normalize] could not write {file_path}: {e}")
            return
