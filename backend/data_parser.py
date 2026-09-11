"""
Data parser for all CSV cutoff files.
Normalizes all formats into a unified list of dicts.
"""

import csv
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Category code → human-readable label
CATEGORY_MAP = {
    "GOPENS": "OPEN (General)",
    "LOPENS": "OPEN (Ladies)",
    "GSCS":   "SC (General)",
    "LSCS":   "SC (Ladies)",
    "GSTS":   "ST (General)",
    "LSTS":   "ST (Ladies)",
    "GOBCS":  "OBC (General)",
    "LOBCS":  "OBC (Ladies)",
    "GSEBCS": "OBC-SEBC (General)",
    "LSEBCS": "OBC-SEBC (Ladies)",
    "GNT1S":  "NT1 (General)",
    "LNT1S":  "NT1 (Ladies)",
    "GNT2S":  "NT2 (General)",
    "LNT2S":  "NT2 (Ladies)",
    "GNT3S":  "NT3 (General)",
    "LNT3S":  "NT3 (Ladies)",
    "GVJS":   "VJ/DT (General)",
    "LVJS":   "VJ/DT (Ladies)",
    "PWDOPENS": "PWD (OPEN)",
    "DEFOPENS": "Defence (OPEN)",
    "TFWS":   "TFWS",
    "ORPHAN": "Orphan",
    "EWSS":   "EWS",
    # Pharma / DSY codes
    "GOPENH": "OPEN (General)",
    "LOPENH": "OPEN (Ladies)",
    "GSCH":   "SC (General)",
    "LSCH":   "SC (Ladies)",
    "GSTH":   "ST (General)",
    "LSTH":   "ST (Ladies)",
    "GOBCH":  "OBC (General)",
    "LOBCH":  "OBC (Ladies)",
    "GSEBCH": "OBC-SEBC (General)",
    "LSEBCH": "OBC-SEBC (Ladies)",
    "GNT1H":  "NT1 (General)",
    "GNT2H":  "NT2 (General)",
    "GNT3H":  "NT3 (General)",
    "GVJH":   "VJ/DT (General)",
    "PWDOPENH":"PWD (OPEN)",
    "MINOPENH":"Minority (OPEN)",
    # DSY Engg
    "GOPEN":  "OPEN (General)",
    "LOPEN":  "OPEN (Ladies)",
    "GSC":    "SC (General)",
    "LSC":    "SC (Ladies)",
    "GST":    "ST (General)",
    "LST":    "ST (Ladies)",
    "GOBC":   "OBC (General)",
    "LOBC":   "OBC (Ladies)",
    "GSEBC":  "OBC-SEBC (General)",
    "LSEBC":  "OBC-SEBC (Ladies)",
    "GNT1":   "NT1 (General)",
    "GNT2":   "NT2 (General)",
    "GNT3":   "NT3 (General)",
    "GVJ":    "VJ/DT (General)",
    "EWS":    "EWS",
    "PWDOPEN":"PWD (OPEN)",
    # Diploma
    "NGOPENH":"OPEN (General)",
    "NLOPENH":"OPEN (Ladies)",
    "NGSCH":  "SC (General)",
    "NLSCH":  "SC (Ladies)",
    "NGSTH":  "ST (General)",
    "NLSTH":  "ST (Ladies)",
    "NGNTAH": "NT-A (General)",
    "NGNTBH": "NT-B (General)",
    "NGOBCH": "OBC (General)",
    "NLOBCH": "OBC (Ladies)",
    "PWDOPENH":"PWD (OPEN)",
    "TGOPENH":"Technical OPEN (General)",
    "TLOPENH":"Technical OPEN (Ladies)",
}

def normalize_category(code):
    code = code.strip().upper()
    return CATEGORY_MAP.get(code, code)

def extract_college_type(status_str):
    s = status_str.lower()
    if "government autonomous" in s or "autonomous institute" in s:
        return "Government Autonomous"
    if "government aided" in s or "govt aided" in s:
        return "Government Aided"
    if "government" in s or "govt" in s:
        return "Government"
    if "university" in s and "department" in s:
        return "University Department"
    if "un-aided" in s or "unaided" in s:
        return "Un-Aided"
    return "Private"

def extract_home_university(status_str):
    m = re.search(r'Home University\s*:\s*([^,;]+)', status_str, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""

def get_chance(user_pct, cutoff_pct):
    diff = float(user_pct) - float(cutoff_pct)
    if diff >= 3:
        return "Safe"
    elif diff >= 0:
        return "Moderate"
    else:
        return "Ambitious"


# ─── Parser 1: CAP Engineering (CAP_All_Rounds_2025.csv) ─────────────────────

def parse_cap_engg():
    fpath = os.path.join(DATA_DIR, "CAP_All_Rounds_2025.csv")
    records = []
    with open(fpath, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "")
            records.append({
                "exam_type":     "CET",
                "cap_round":     row.get("cap_round", "").strip(),
                "college_code":  row.get("college_code", "").strip(),
                "college_name":  row.get("college_name", "").strip(),
                "branch_code":   row.get("branch_code", "").strip(),
                "branch_name":   row.get("branch_name", "").strip(),
                "college_type":  extract_college_type(status),
                "home_university": extract_home_university(status),
                "level":         row.get("level", "").strip(),
                "category_code": row.get("category", "").strip().upper(),
                "category":      normalize_category(row.get("category", "")),
                "cutoff_rank":   row.get("cutoff_rank", "").strip(),
                "cutoff_percentile": row.get("cutoff_percentile", "").strip(),
            })
    return records


# ─── Parser 2: Pharmacy CAP files (2025PHARMA_CAP*.csv.xls) ──────────────────

def _parse_pharma_file(fpath, cap_round):
    """
    These files have a complex report format.
    Structure per college/course:
      - College code & name line: e.g. "01003 - Government College of Pharmacy, Amravati"
      - Course line:              e.g. "0100310010 - Pharm D..."
      - Status line
      - Home University block label
      - "Stage" line
      - Blank
      - Category codes line (space-separated)
      - Blank
      - [category code]  repeated per category as single cell rows
      then rank row, then percentile row
    
    We'll collect all text and use the pattern:
    college → course → category_code → rank (percentile)
    """
    records = []
    with open(fpath, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        lines = [row for row in reader]

    college_name = ""
    college_code = ""
    branch_name  = ""
    branch_code  = ""
    college_type = ""
    i = 0

    while i < len(lines):
        row = lines[i]
        # Skip empty
        if not any(c.strip() for c in row):
            i += 1
            continue

        cell = row[0].strip()

        # Detect college line: starts with 5-digit code like "01003 - College Name"
        m_college = re.match(r'^(\d{5})\s*-\s*(.+)', cell)
        if m_college:
            college_code = m_college.group(1)
            college_name = m_college.group(2).strip()
            i += 1
            continue

        # Detect branch/course line: starts with 10-digit code
        m_branch = re.match(r'^(\d{10})\s*-\s*(.+)', cell)
        if m_branch:
            branch_code = m_branch.group(1)
            branch_name = m_branch.group(2).strip()
            i += 1
            continue

        # Detect status line
        if cell.lower().startswith("status:"):
            college_type = extract_college_type(cell)
            i += 1
            continue

        # Detect category header row: cells that look like category codes
        # A row of GOPENH LOPENH GSCH etc.
        cat_pattern = re.compile(r'^[GL][A-Z0-9]{2,8}$|^PWDOPEN|^MINOPENH|^EWS|^TFWS|^DEF')
        if all(cat_pattern.match(c.strip()) for c in row if c.strip()):
            cats = [c.strip() for c in row if c.strip()]
            # Next non-empty row = ranks, row after = percentile row with "Stage-N (xx%)"
            i += 1
            # Skip empties
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines):
                break
            rank_row = [c.strip() for c in lines[i] if c.strip()]
            i += 1
            # percentile row may look like: "Stage-I (96.14%) (93.45%) ..."
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines):
                break
            pct_row_raw = lines[i]
            pct_row = [c.strip() for c in pct_row_raw if c.strip()]
            i += 1

            # Extract percentiles from "(xx.xx%)" patterns
            pcts = re.findall(r'\((\d+\.?\d*)\s*%?\)', " ".join(pct_row))

            for j, cat in enumerate(cats):
                rank = rank_row[j] if j < len(rank_row) else ""
                pct  = pcts[j]   if j < len(pcts)     else ""
                if rank or pct:
                    records.append({
                        "exam_type":       "Pharmacy",
                        "cap_round":       cap_round,
                        "college_code":    college_code,
                        "college_name":    college_name,
                        "branch_code":     branch_code,
                        "branch_name":     branch_name,
                        "college_type":    college_type,
                        "home_university": "",
                        "level":           "State Level",
                        "category_code":   cat.upper(),
                        "category":        normalize_category(cat),
                        "cutoff_rank":     rank,
                        "cutoff_percentile": pct,
                    })
            continue

        # Single-cell category code rows (alternate layout)
        if len([c for c in row if c.strip()]) == 1 and cat_pattern.match(cell):
            cat = cell
            # next non-empty = rank
            i += 1
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            rank_cell = lines[i][0].strip()
            i += 1
            # next = percentile in format "(xx.xx%)"
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            pct_cell = lines[i][0].strip()
            pcts = re.findall(r'\((\d+\.?\d*)\s*%?\)', pct_cell)
            pct = pcts[0] if pcts else ""
            records.append({
                "exam_type":       "Pharmacy",
                "cap_round":       cap_round,
                "college_code":    college_code,
                "college_name":    college_name,
                "branch_code":     branch_code,
                "branch_name":     branch_name,
                "college_type":    college_type,
                "home_university": "",
                "level":           "State Level",
                "category_code":   cat.upper(),
                "category":        normalize_category(cat),
                "cutoff_rank":     rank_cell,
                "cutoff_percentile": pct,
            })
            continue

        i += 1

    return records


def parse_pharma():
    files = [
        ("2025PHARMA_CAP1_CutOff.csv.xls",    "CAP1"),
        ("2025PHARMA_CAP2_CutOff.csv.xls",    "CAP2"),
        ("2025PHARMA_CAP3_CutOff.csv.xls",    "CAP3"),
        ("2025PHARMA_CAP2_AI_CutOff.csv.xls", "CAP2-AI"),
        ("2025PHARMA_CAP3_AI_CutOff.csv.xls", "CAP3-AI"),
        ("2025PHARMA_CAP4_AI_CutOff.csv.xls", "CAP4-AI"),
    ]
    all_records = []
    for fname, cap_round in files:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            recs = _parse_pharma_file(fpath, cap_round)
            all_records.extend(recs)
    return all_records


# ─── Parser 3: DSY Engineering (DSY round 1/2 cap.csv.xls) ───────────────────

def _parse_dsy_engg_file(fpath, cap_round):
    """
    Format:
      "1002 Government College of Engineering"
      "Choice Code : 100219110 Course Name : Civil Engineering"
      "GOPEN GST GOBC LOPEN LSC LSEBC EWS"   (category headers)
      "1282 28609 1927 1147 2355 5376 4977"   (ranks)
      "Stage-I (92.74%) (76.79%) ..."         (percentiles)
    """
    records = []
    with open(fpath, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        lines = [row for row in reader]

    college_name = ""
    college_code = ""
    branch_name  = ""
    branch_code  = ""
    i = 0

    while i < len(lines):
        row = lines[i]
        if not any(c.strip() for c in row):
            i += 1
            continue
        cell = row[0].strip()

        # College line: "1002 Government College of Engineering"
        m_col = re.match(r'^(\d{4})\s+(.+)', cell)
        if m_col and "Choice Code" not in cell and "Stage" not in cell:
            college_code = m_col.group(1)
            college_name = m_col.group(2).strip()
            i += 1
            continue

        # Course line: "Choice Code : 100219110 Course Name : Civil Engineering"
        m_course = re.match(r'Choice Code\s*:\s*(\d+)\s+Course Name\s*:\s*(.+)', cell, re.IGNORECASE)
        if m_course:
            branch_code = m_course.group(1)
            branch_name = m_course.group(2).strip()
            i += 1
            continue

        # Category header row: all caps codes separated by spaces
        cat_codes = cell.split()
        valid_cats = [c for c in cat_codes if re.match(r'^[GL][A-Z0-9]{2,6}$|^EWS$|^TFWS$|^PWD', c)]
        if len(valid_cats) >= 2 and len(valid_cats) == len(cat_codes):
            cats = cat_codes
            i += 1
            # rank row
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            rank_vals = lines[i][0].strip().split() if lines[i] else []
            i += 1
            # percentile row
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            pct_line = " ".join(lines[i])
            pcts = re.findall(r'\((\d+\.?\d*)\s*%?\)', pct_line)
            i += 1

            for j, cat in enumerate(cats):
                rank = rank_vals[j] if j < len(rank_vals) else ""
                pct  = pcts[j]      if j < len(pcts)      else ""
                if rank or pct:
                    records.append({
                        "exam_type":       "DSY_Engineering",
                        "cap_round":       cap_round,
                        "college_code":    college_code,
                        "college_name":    college_name,
                        "branch_code":     branch_code,
                        "branch_name":     branch_name,
                        "college_type":    "Government",
                        "home_university": "",
                        "level":           "State Level",
                        "category_code":   cat.upper(),
                        "category":        normalize_category(cat),
                        "cutoff_rank":     rank,
                        "cutoff_percentile": pct,
                    })
            continue

        i += 1

    return records


def parse_dsy_engg():
    files = [
        ("DSY round 1 cap.csv.xls", "CAP1"),
        ("DSY round 2 cap.csv.xls", "CAP2"),
    ]
    all_records = []
    for fname, cap_round in files:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            recs = _parse_dsy_engg_file(fpath, cap_round)
            all_records.extend(recs)
    return all_records


# ─── Parser 4: Diploma (Diploma 25 round 1/2.csv.xls) ────────────────────────

def _parse_diploma_file(fpath, cap_round):
    """
    Multi-column format:
      Row: "1006 - Government Polytechnic, Murtijapur" (college line)
      Row: "100619110 - Civil Engineering"              (branch line)
      Row: "Status : Government"
      Row: "Home District Seats" / "Technical Seats" labels
      Row: category codes (multi-column, each category in own cell)
      Row: (blank)
      Row: ranks (multi-column)
      Row: "Stage-I" label
      Row: (blank)
      Row: percentiles in (xx.xx) format (multi-column)
    """
    records = []
    with open(fpath, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        lines = [row for row in reader]

    college_name = ""
    college_code = ""
    branch_name  = ""
    branch_code  = ""
    college_type = "Government"
    i = 0

    while i < len(lines):
        row = lines[i]
        cells = [c.strip() for c in row]
        non_empty = [c for c in cells if c]

        if not non_empty:
            i += 1
            continue

        cell = non_empty[0]

        # College line multi-col: "1006 - Government Polytechnic ..."
        # Sometimes spread across cells
        full_line = " ".join(non_empty)
        m_col = re.match(r'^(\d{4})\s*-\s*(.+)', full_line)
        if m_col:
            college_code = m_col.group(1)
            college_name = m_col.group(2).strip()
            i += 1
            continue

        # Branch line
        m_branch = re.match(r'^(\d{9,10})\s*-\s*(.+)', full_line)
        if m_branch:
            branch_code = m_branch.group(1)
            branch_name = m_branch.group(2).strip()
            i += 1
            continue

        # Status
        if full_line.lower().startswith("status"):
            college_type = extract_college_type(full_line)
            i += 1
            continue

        # Category header row: cells like NGOPENH, NGSCH etc. or TGOPENH
        cat_pattern = re.compile(r'^[NTG][A-Z0-9]{3,8}$|^PWDOPEN')
        if sum(1 for c in non_empty if cat_pattern.match(c)) >= 2:
            cats = [c for c in cells if cat_pattern.match(c)]
            cat_indices = [idx for idx, c in enumerate(cells) if cat_pattern.match(c)]
            i += 1

            # Skip blank rows
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            rank_cells = lines[i]
            i += 1

            # Skip "Stage-I" label row
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            if "Stage" in " ".join(lines[i]):
                i += 1
                while i < len(lines) and not any(c.strip() for c in lines[i]):
                    i += 1

            if i >= len(lines): break
            pct_cells = lines[i]
            i += 1

            for j, cat in enumerate(cats):
                idx = cat_indices[j] if j < len(cat_indices) else j
                rank = rank_cells[idx].strip() if idx < len(rank_cells) else ""
                pct_raw = pct_cells[idx].strip() if idx < len(pct_cells) else ""
                pct_m = re.search(r'\((\d+\.?\d*)\)', pct_raw)
                pct = pct_m.group(1) if pct_m else pct_raw.strip("()")

                if rank or pct:
                    records.append({
                        "exam_type":       "Diploma",
                        "cap_round":       cap_round,
                        "college_code":    college_code,
                        "college_name":    college_name,
                        "branch_code":     branch_code,
                        "branch_name":     branch_name,
                        "college_type":    college_type,
                        "home_university": "",
                        "level":           "State Level",
                        "category_code":   cat.upper(),
                        "category":        normalize_category(cat),
                        "cutoff_rank":     rank,
                        "cutoff_percentile": pct,
                    })
            continue

        i += 1

    return records


def parse_diploma():
    files = [
        ("Diploma 25 round 1.csv.xls", "CAP1"),
        ("Diploma 25 round 2.csv.xls", "CAP2"),
    ]
    all_records = []
    for fname, cap_round in files:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            recs = _parse_diploma_file(fpath, cap_round)
            all_records.extend(recs)
    return all_records


# ─── Parser 5: DSY Pharmacy (DSY pharmacy round 2 25.csv.xls) ────────────────

def parse_dsy_pharmacy():
    """
    Same format as DSY Engineering but for pharmacy.
    "1003 Government College of Pharmacy"
    "Choice Code : 100382310 Course Name : Pharmacy"
    "GOPEN LSC"
    "137 1378"
    "Stage-I (86.91%) (79.09%)"
    """
    fpath = os.path.join(DATA_DIR, "DSY pharmacy round 2 25.csv.xls")
    if not os.path.exists(fpath):
        return []

    records = []
    with open(fpath, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        lines = [row for row in reader]

    college_name = ""
    college_code = ""
    branch_name  = "Pharmacy"
    branch_code  = ""
    i = 0

    while i < len(lines):
        row = lines[i]
        if not any(c.strip() for c in row):
            i += 1
            continue
        cell = row[0].strip()

        m_col = re.match(r'^(\d{4})\s+(.+)', cell)
        if m_col and "Choice Code" not in cell:
            college_code = m_col.group(1)
            college_name = m_col.group(2).strip()
            i += 1
            continue

        m_course = re.match(r'Choice Code\s*:\s*(\d+)\s+Course Name\s*:\s*(.+)', cell, re.IGNORECASE)
        if m_course:
            branch_code = m_course.group(1)
            branch_name = m_course.group(2).strip()
            i += 1
            continue

        cat_codes = cell.split()
        valid_cats = [c for c in cat_codes if re.match(r'^[GL][A-Z0-9]{2,6}$|^EWS$', c)]
        if len(valid_cats) >= 1 and len(valid_cats) == len(cat_codes):
            cats = cat_codes
            i += 1
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            rank_vals = lines[i][0].strip().split()
            i += 1
            while i < len(lines) and not any(c.strip() for c in lines[i]):
                i += 1
            if i >= len(lines): break
            pct_line = " ".join(lines[i])
            pcts = re.findall(r'\((\d+\.?\d*)\s*%?\)', pct_line)
            i += 1

            for j, cat in enumerate(cats):
                rank = rank_vals[j] if j < len(rank_vals) else ""
                pct  = pcts[j]      if j < len(pcts)      else ""
                if rank or pct:
                    records.append({
                        "exam_type":       "DSY_Pharmacy",
                        "cap_round":       "CAP2",
                        "college_code":    college_code,
                        "college_name":    college_name,
                        "branch_code":     branch_code,
                        "branch_name":     branch_name,
                        "college_type":    "Government",
                        "home_university": "",
                        "level":           "State Level",
                        "category_code":   cat.upper(),
                        "category":        normalize_category(cat),
                        "cutoff_rank":     rank,
                        "cutoff_percentile": pct,
                    })
            continue

        i += 1

    return records


# ─── Master loader ─────────────────────────────────────────────────────────────

_cache = {}

def load_all_data():
    global _cache
    if _cache:
        return _cache

    print("Loading CET Engineering data...")
    cet = parse_cap_engg()
    print(f"  → {len(cet)} records")

    print("Loading Pharmacy data...")
    pharma = parse_pharma()
    print(f"  → {len(pharma)} records")

    print("Loading DSY Engineering data...")
    dsy_engg = parse_dsy_engg()
    print(f"  → {len(dsy_engg)} records")

    print("Loading Diploma data...")
    diploma = parse_diploma()
    print(f"  → {len(diploma)} records")

    print("Loading DSY Pharmacy data...")
    dsy_pharma = parse_dsy_pharmacy()
    print(f"  → {len(dsy_pharma)} records")

    _cache = {
        "CET":          cet,
        "Pharmacy":     pharma,
        "DSY_Engineering": dsy_engg,
        "Diploma":      diploma,
        "DSY_Pharmacy": dsy_pharma,
    }
    total = sum(len(v) for v in _cache.values())
    print(f"Total records loaded: {total}")
    return _cache


def get_meta(exam_type):
    """Return unique branches, categories, rounds, college_types, universities for an exam type."""
    data = load_all_data()
    recs = data.get(exam_type, [])

    branches      = sorted(set(r["branch_name"] for r in recs if r["branch_name"]))
    categories    = sorted(set(r["category"]    for r in recs if r["category"]))
    rounds        = sorted(set(r["cap_round"]   for r in recs if r["cap_round"]))
    college_types = sorted(set(r["college_type"] for r in recs if r["college_type"]))
    universities  = sorted(set(r["home_university"] for r in recs if r["home_university"]))

    return {
        "branches":      branches,
        "categories":    categories,
        "rounds":        rounds,
        "college_types": college_types,
        "universities":  universities,
    }


if __name__ == "__main__":
    d = load_all_data()
    for k, v in d.items():
        print(f"{k}: {len(v)} records")
        if v:
            print(f"  Sample: {v[0]}")
