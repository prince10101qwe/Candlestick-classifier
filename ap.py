# app.py — Candlestick Identifier (Strict, Final Rules, Robust)
import streamlit as st
import re

st.set_page_config(page_title="Candlestick Identifier — Strict Rules", layout="centered")
st.title("Candlestick Identifier — Strict Rules + Full Comparison")

raw = st.text_area(
    "Paste OHLC per line (any format). Examples:\n"
    "O3,937.630 H3,940.880 L3,934.140 C3,937.540\n"
    "3992.270,3994.745,3990.740,3992.195",
    height=180,
)
show_debug = st.checkbox("Show debug metrics")

# ---------------------- Final Rule Thresholds ----------------------
DOJI_BODY_MAX = 10.0          # Doji body% 0–10
DOJI_WICK_RATIO_MAX = 1.20    # Doji wicks roughly equal (≤20% diff)

PINBAR_BODY_MAX = 20.0        # Pin Bar body% <20

LWR_BODY_MAX = 30.0           # Long Wick Rejection body% ≤30
LWR_OPP_RATIO = 0.25          # Opposite wick ≤ 1/4 of dominant

SPIN_BODY_MIN = 10.0          # Spinning Top body% 10–30
SPIN_BODY_MAX = 30.0
SPIN_WICK_RATIO_MAX = 1.40    # Spinning wicks roughly equal (≤40% diff)

# ---------------------- Parsing ----------------------
def parse_line(line: str):
    """Parse one line. Prefer labeled O/H/L/C in any order. Fallback: first 4 numbers."""
    s = line.replace(",", "")  # remove thousands separators
    # labeled capture
    lab = {}
    for key in ["O", "H", "L", "C", "o", "h", "l", "c"]:
        m = re.search(key + r"\s*([-+]?\d*\.?\d+)", s)
        if m:
            lab[key.upper()] = float(m.group(1))
    if all(k in lab for k in ["O", "H", "L", "C"]):
        return lab["O"], lab["H"], lab["L"], lab["C"], line.strip()

    # fallback: first 4 numbers
    nums = re.findall(r"[-+]?\d*\.?\d+", s)
    if len(nums) >= 4:
        o, h, l, c = map(float, nums[:4])
        return o, h, l, c, line.strip()
    return None

# ---------------------- Classifier ----------------------
def classify(o, h, l, c):
    # Validation
    if l >= h:
        return {"final": ("Invalid Candle", "LOW ≥ HIGH."), "comparison": ["All patterns skipped."], "dbg": {}}
    big = max(abs(o), abs(h), abs(l), abs(c))
    if big > 10_000_000:
        return {"final": ("Invalid Candle", "Unreasonable magnitude (formatting)."), "comparison": ["Check commas/labels."], "dbg": {}}
    rng = h - l
    if rng < 1e-9:
        return {"final": ("Invalid Candle", "Range too small."), "comparison": ["High≈Low."], "dbg": {}}

    # Metrics
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    body_pct = 100.0 * body / rng
    if body_pct > 500:  # corrupted
        return {"final": ("Invalid Candle", f"Body% {body_pct:.2f}% (corrupted input)."), "comparison": ["Range tiny or parse error."], "dbg": {}}

    eps = 1e-12
    wick_ratio = max(upper, lower) / max(min(upper, lower), eps)

    # Rule checks (booleans + reasons)
    results = {}

    # 1) Doji (standard)
    results["Doji"] = (
        body_pct <= DOJI_BODY_MAX and upper >= body and lower >= body and wick_ratio <= DOJI_WICK_RATIO_MAX,
        f"body {body_pct:.2f}% ≤ {DOJI_BODY_MAX}%, upper≥body({upper:.6g}≥{body:.6g}), "
        f"lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤{DOJI_WICK_RATIO_MAX} ({wick_ratio:.2f})"
        if body_pct <= DOJI_BODY_MAX else f"body {body_pct:.2f}% > {DOJI_BODY_MAX}%"
    )

    # 2) Bullish Doji (Dragonfly)
    results["Bullish Doji (Dragonfly)"] = (
        body_pct <= DOJI_BODY_MAX and lower >= 2.0 * body and upper <= 0.10 * lower,
        f"body {body_pct:.2f}% ≤{DOJI_BODY_MAX}%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, "
        f"upper {upper:.6g} ≤ 10% of lower {0.1*lower:.6g}"
    )

    # 3) Bearish Doji (Gravestone)
    results["Bearish Doji (Gravestone)"] = (
        body_pct <= DOJI_BODY_MAX and upper >= 2.0 * body and lower <= 0.10 * upper,
        f"body {body_pct:.2f}% ≤{DOJI_BODY_MAX}%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, "
        f"lower {lower:.6g} ≤ 10% of upper {0.1*upper:.6g}"
    )

    # 4) Bullish Pin Bar
    results["Bullish Pin Bar"] = (
        body_pct < PINBAR_BODY_MAX and lower >= 2.0 * body and upper <= body,
        f"body {body_pct:.2f}% <{PINBAR_BODY_MAX}%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ body {body:.6g}"
    )

    # 5) Bearish Pin Bar
    results["Bearish Pin Bar"] = (
        body_pct < PINBAR_BODY_MAX and upper >= 2.0 * body and lower <= body,
        f"body {body_pct:.2f}% <{PINBAR_BODY_MAX}%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ body {body:.6g}"
    )

    # 6) Bullish Long Wick Rejection (LWR)
    results["Bullish Long Wick Rejection"] = (
        body_pct <= LWR_BODY_MAX and lower >= 2.0 * body and upper <= LWR_OPP_RATIO * lower,
        f"body {body_pct:.2f}% ≤{LWR_BODY_MAX}%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ ¼ lower {LWR_OPP_RATIO*lower:.6g}"
    )

    # 7) Bearish Long Wick Rejection (LWR)
    results["Bearish Long Wick Rejection"] = (
        body_pct <= LWR_BODY_MAX and upper >= 2.0 * body and lower <= LWR_OPP_RATIO * upper,
        f"body {body_pct:.2f}% ≤{LWR_BODY_MAX}%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ ¼ upper {LWR_OPP_RATIO*upper:.6g}"
    )

    # 8) Spinning Top
    results["Spinning Top"] = (
        (SPIN_BODY_MIN <= body_pct <= SPIN_BODY_MAX) and (upper >= body) and (lower >= body) and (wick_ratio <= SPIN_WICK_RATIO_MAX),
        f"body {body_pct:.2f}% in [{SPIN_BODY_MIN:.0f},{SPIN_BODY_MAX:.0f}], upper≥body({upper:.6g}≥{body:.6g}), "
        f"lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤{SPIN_WICK_RATIO_MAX} ({wick_ratio:.2f})"
        if SPIN_BODY_MIN <= body_pct <= SPIN_BODY_MAX else f"body {body_pct:.2f}% not in [{SPIN_BODY_MIN:.0f},{SPIN_BODY_MAX:.0f}]"
    )

    # Pin Bar -> LWR conversion only if LWR also matches (your rule)
    # Implement via priority selection, not force-convert here.

    # Priority (strongest → weakest)
    priority = [
        "Bullish Doji (Dragonfly)",
        "Bearish Doji (Gravestone)",
        "Doji",
        "Bullish Pin Bar",
        "Bearish Pin Bar",
        "Bullish Long Wick Rejection",
        "Bearish Long Wick Rejection",
        "Spinning Top",
    ]

    # Select highest-priority match
    final_type, final_reason = "Normal Candle", f"body {body_pct:.2f}% — no rule matched"
    for name in priority:
        ok, why = results[name]
        if ok:
            final_type, final_reason = name, why
            break

    # Comparison: why not others (or note lower-priority matches)
    comparison = []
    for name in priority:
        ok, why = results[name]
        if name == final_type:
            continue
        if ok:
            comparison.append(f"- {name}: matched, but lower priority than {final_type}")
        else:
            comparison.append(f"- Not {name}: {why}")

    dbg = dict(
        O=o, H=h, L=l, C=c, range=rng, body=body, upper=upper, lower=lower,
        body_pct=body_pct, wick_ratio=wick_ratio
    )
    return {"final": (final_type, final_reason), "comparison": comparison, "dbg": dbg}

# ---------------------- Run ----------------------
if st.button("Analyze"):
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        st.error("No input.")
    else:
        for i, line in enumerate(lines, 1):
            parsed = parse_line(line)
            st.subheader(f"Candle {i}")
            st.caption(line.strip())
            if not parsed:
                st.write("**Type:** Invalid Candle")
                st.write("**Reason:** Could not parse 4 numbers (O,H,L,C).")
                st.write("---")
                continue
            o, h, l, c, orig = parsed
            rep = classify(o, h, l, c)
            t, why = rep["final"]
            st.write(f"**Candle Type:** {t}")
            st.write(f"**Reason:** {why}")
            st.write("**Comparison:**")
            for row in rep["comparison"]:
                st.write(row)
            if show_debug:
                st.write("**Debug:**", rep["dbg"])
            st.write("---")
