"""
Prediction engine: filters and ranks college records based on user inputs.
"""

from data_parser import load_all_data, get_chance


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def predict(params):
    """
    params dict keys (all optional except exam_type and score):
      exam_type       : "CET" | "Pharmacy" | "DSY_Engineering" | "Diploma" | "DSY_Pharmacy"
      percentile      : float (user's percentile/percentage)
      rank            : int   (user's rank, for rank-based exams)
      cap_round       : "CAP1" | "CAP2" | "CAP3" | "CAP4" | "" (blank = all rounds)
      branch          : str (partial match, "" = all branches)
      category        : str (human-readable, e.g. "OPEN (General)", "" = all)
      college_type    : str ("Government" etc., "" = all)
      home_university : str ("" = all)
      gender          : "Male" | "Female" | "Other" | "" (Male → General seats only, Female → Ladies too)
      tfws            : bool
      level           : "State Level" | "Home University" | "" = all
    
    Returns list of result dicts sorted best-fit first.
    """
    exam_type   = params.get("exam_type", "CET")
    user_pct    = _safe_float(params.get("percentile", 0))
    user_rank   = _safe_float(params.get("rank", 0))
    cap_round   = params.get("cap_round", "").strip()
    branch_q    = params.get("branch", "").strip().lower()
    category_q  = params.get("category", "").strip().lower()
    ctype_q     = params.get("college_type", "").strip().lower()
    univ_q      = params.get("home_university", "").strip().lower()
    gender      = params.get("gender", "").strip()
    tfws        = params.get("tfws", False)
    level_q     = params.get("level", "").strip().lower()

    all_data = load_all_data()
    records  = all_data.get(exam_type, [])

    results = []

    for r in records:
        # ── Round filter ────────────────────────────────────────────────────
        if cap_round and r["cap_round"] != cap_round:
            continue

        # ── Branch filter ───────────────────────────────────────────────────
        if branch_q and branch_q not in r["branch_name"].lower():
            continue

        # ── Category filter ─────────────────────────────────────────────────
        if tfws:
            if "tfws" not in r["category_code"].lower() and "tfws" not in r["category"].lower():
                continue
        elif category_q:
            if category_q not in r["category"].lower():
                continue

        # ── Gender filter ───────────────────────────────────────────────────
        # Ladies seats contain "Ladies" in category
        if gender == "Male":
            if "ladies" in r["category"].lower():
                continue
        # Female can see both general and ladies seats (no filter needed)

        # ── College type filter ─────────────────────────────────────────────
        if ctype_q and ctype_q not in r["college_type"].lower():
            continue

        # ── University filter ───────────────────────────────────────────────
        if univ_q and r["home_university"] and univ_q not in r["home_university"].lower():
            continue

        # ── Level filter ────────────────────────────────────────────────────
        if level_q and r["level"] and level_q not in r["level"].lower():
            continue

        # ── Score comparison ─────────────────────────────────────────────────
        cutoff_pct  = _safe_float(r["cutoff_percentile"])
        cutoff_rank = _safe_float(r["cutoff_rank"])

        eligible = False
        chance   = "Unknown"
        score_gap = 0

        if user_pct is not None and cutoff_pct is not None and cutoff_pct > 0:
            diff = user_pct - cutoff_pct
            score_gap = diff
            if diff >= 0:       # within 5 percentile points below cutoff = show as ambitious
                eligible = True
                chance = get_chance(user_pct, cutoff_pct)

        elif user_rank is not None and cutoff_rank is not None and cutoff_rank > 0:
            diff = cutoff_rank - user_rank   # positive = user rank is better (lower number)
            score_gap = diff
            if diff >= -5000:    # within 5000 rank points
                eligible = True
                if diff >= 2000:
                    chance = "Safe"
                elif diff >= 0:
                    chance = "Moderate"
                else:
                    chance = "Ambitious"

        if not eligible:
            continue

        results.append({
            "college_code":      r["college_code"],
            "college_name":      r["college_name"],
            "branch_name":       r["branch_name"],
            "cap_round":         r["cap_round"],
            "category":          r["category"],
            "college_type":      r["college_type"],
            "home_university":   r["home_university"],
            "level":             r["level"],
            "cutoff_rank":       r["cutoff_rank"],
            "cutoff_percentile": r["cutoff_percentile"],
            "chance":            chance,
            "score_gap":         round(score_gap, 4),
        })

    # Sort: Safe first → Moderate → Ambitious; within same tier sort by score_gap desc
    chance_order = {"Safe": 0, "Moderate": 1, "Ambitious": 2, "Unknown": 3}
    results.sort(key=lambda x: (chance_order.get(x["chance"], 3), -x["score_gap"]))

    # De-duplicate (same college + branch + category, keep best round)
    seen = set()
    deduped = []
    for r in results:
        key = (r["college_code"], r["branch_name"], r["category"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped
