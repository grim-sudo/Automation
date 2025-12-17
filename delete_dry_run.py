import re
import os
from omni_automator.core.ai_task_executor import AITaskExecutor

# Prompt to dry-run
prompt = "delete fodlers named x and y and z so from 1 to 10 from Test\\c_ fodler"

def parse_delete_prompt(cmd: str):
    """Parse prefixes, range and base folder from a natural prompt."""
    # Normalize spaces and common misspellings
    s = cmd.lower()
    s = s.replace('fodlers', 'folders').replace('fodler', 'folder')

    # Extract prefixes list: e.g., 'named x and y and z' or 'named x,y,z'
    prefixes = []
    m = re.search(r"named\s+([a-z0-9_,\s]+?)\s+(?:so|from)\s+", s)
    if m:
        raw = m.group(1)
        parts = re.split(r",|and|\s+", raw)
        prefixes = [p.strip() for p in parts if p.strip()]

    # Extract numeric range: 'from 1 to 10' or '1..10'
    start = 1
    end = None
    m2 = re.search(r"from\s*(\d{1,4})\s*to\s*(\d{1,4})", s)
    if m2:
        start = int(m2.group(1))
        end = int(m2.group(2))
    else:
        m3 = re.search(r"(\d{1,4})\s*\.\.\s*(\d{1,4})", s)
        if m3:
            start = int(m3.group(1)); end = int(m3.group(2))

    # Extract base folder after 'from' like 'from Test\c_ folder' or 'inside C:\path'
    base = None
    m4 = re.search(r"from\s+([\w\\/\s\-_.]+?)\s+folder", s)
    if m4:
        base = m4.group(1).strip()
    else:
        m5 = re.search(r"inside\s+([\w:\\\/\s\-_.]+)", s)
        if m5:
            base = m5.group(1).strip()

    return prefixes, start, end, base


def resolve_base(executor: AITaskExecutor, base_hint: str):
    # Try absolute path first
    if not base_hint:
        return None
    # Normalize backslashes
    candidate = base_hint.replace('\\', os.sep).replace('/', os.sep).strip()
    # If it's like 'c:\path' and exists, use it
    if os.path.isabs(candidate) and os.path.exists(candidate):
        return os.path.abspath(candidate)
    # Otherwise try resolve with executor helper
    resolved = executor._resolve_file_with_disambiguation(candidate)
    if resolved:
        return resolved
    # Try on Desktop
    desktop = os.path.expanduser('~/Desktop')
    cand2 = os.path.join(desktop, candidate)
    if os.path.exists(cand2):
        return os.path.abspath(cand2)
    return None

if __name__ == '__main__':
    executor = AITaskExecutor()
    prefixes, start, end, base_hint = parse_delete_prompt(prompt)

    print('Parsed: prefixes=', prefixes, 'range=', (start, end), 'base_hint=', base_hint)

    base_path = resolve_base(executor, base_hint)
    if not base_path:
        print('Could not resolve base folder:', base_hint)
        print('No deletion will be performed in dry-run.')
        raise SystemExit(1)

    print('Resolved base path:', base_path)

    if end is None:
        print('No end of range parsed; aborting dry-run')
        raise SystemExit(1)

    # Build list of target paths
    targets = []
    for p in prefixes:
        for i in range(start, end + 1):
            name = f"{p}{i}"
            targets.append(os.path.join(base_path, name))

    # Report which of these exist and which don't
    existing = [t for t in targets if os.path.exists(t)]
    missing = [t for t in targets if not os.path.exists(t)]

    result = {
        'requested_count': len(targets),
        'existing_count': len(existing),
        'missing_count': len(missing),
        'existing_paths': existing,
        'missing_paths_sample': missing[:20]
    }

    import json
    print(json.dumps(result, indent=2))
