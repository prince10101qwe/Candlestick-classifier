# app.py — strict rules + labeled parser + debug
import streamlit as st
import re

st.set_page_config(page_title="Candlestick Identifier — Strict", layout="centered")
st.title("Candlestick Identifier — Strict Rules")

raw = st.text_area("Paste lines (any order/format): e.g. O3,937.630 H3,940.880 L3,934.140 C3,937.540", height=180)
show_debug = st.checkbox("Show debug metrics")

# ---------- Robust labeled parser ----------
def parse_line(line: str):
    s = line.replace(",", "")
    # capture labeled values in any order
    lab = dict()
    for key in ["O","H","L","C","o","h","l","c"]:
        m = re.search(key + r"\s*([-+]?\d*\.?\d+)", s)
        if m:
            lab[key.upper()] = float(m.group(1))
    if all(k in lab for k in ["O","H","L","C"]):
        return lab["O"], lab["H"], lab["L"], lab["C"], line.strip()

    # fallback: take first 4 numbers in order
    nums = re.findall(r"[-+]?\d*\.?\d+", s)
    if len(nums) >= 4:
        o, h, l, c = map(float, nums[:4])
        return o, h, l, c, line.strip()
    return None

# ---------- Classifier ----------
def classify(o, h, l, c):
    # validation
    if l >= h:
        return {"final": ("Invalid Candle", "LOW ≥ HIGH."), "comparison": ["All patterns skipped."], "dbg": {}}
    big = max(abs(o), abs(h), abs(l), abs(c))
    if big > 10_000_000:
        return {"final": ("Invalid Candle", "Unreasonable magnitude (formatting)."), "comparison": ["Check commas/labels."], "dbg": {}}
    rng = h - l
    if rng < 1e-9:
        return {"final": ("Invalid Candle", "Range too small."), "comparison": ["High≈Low."], "dbg": {}}

    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    body_pct = 100.0 * body / rng
    if body_pct > 500:
        return {"final": ("Invalid Candle", f"Body% {body_pct:.2f}% (corrupted input)."), "comparison": ["Range tiny or parse error."], "dbg": {}}

    eps = 1e-12
    wick_ratio = max(upper, lower) / max(min(upper, lower), eps)

    # rules
    results = {}
    results["Doji"] = (
        body_pct <= 10.0 and upper >= body and lower >= body and wick_ratio <= 1.2,
        f"body {body_pct:.2f}% ≤ 10%, upper≥body({upper:.6g}≥{body:.6g}), lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤1.2 ({wick_ratio:.2f})"
    )
    results["Bullish Doji (Dragonfly)"] = (
        body_pct <= 10.0 and lower >= 2.0*body and upper <= 0.1*lower,
        f"body {body_pct:.2f}% ≤10%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ 10% of lower {0.1*lower:.6g}"
    )
    results["Bearish Doji (Gravestone)"] = (
        body_pct <= 10.0 and upper >= 2.0*body and lower <= 0.1*upper,
        f"body {body_pct:.2f}% ≤10%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ 10% of upper {0.1*upper:.6g}"
    )
    results["Bullish Pin Bar"] = (
        body_pct < 20.0 and lower >= 2.0*body and upper <= body,
        f"body {body_pct:.2f}% <20%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ body {body:.6g}"
    )
    results["Bearish Pin Bar"] = (
        body_pct < 20.0 and upper >= 2.0*body and lower <= body,
        f"body {body_pct:.2f}% <20%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ body {body:.6g}"
    )
    results["Bullish Long Wick Rejection"] = (
        body_pct <= 30.0 and lower >= 2.0*body and upper <= 0.25*lower,
        f"body {body_pct:.2f}% ≤30%, lower {lower:.6g} ≥ 2×body {2*body:.6g}, upper {upper:.6g} ≤ ¼ lower {0.25*lower:.6g}"
    )
    results["Bearish Long Wick Rejection"] = (
        body_pct <= 30.0 and upper >= 2.0*body and lower <= 0.25*upper,
        f"body {body_pct:.2f}% ≤30%, upper {upper:.6g} ≥ 2×body {2*body:.6g}, lower {lower:.6g} ≤ ¼ upper {0.25*upper:.6g}"
    )
    results["Spinning Top"] = (
        10.0 <= body_pct <= 30.0 and upper >= body and lower >= body and wick_ratio <= 1.4,
        f"body {body_pct:.2f}% in [10,30], upper≥body({upper:.6g}≥{body:.6g}), lower≥body({lower:.6g}≥{body:.6g}), wick ratio ≤1.4 ({wick_ratio:.2f})"
    )

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

    final_type, final_reason = "Normal Candle", f"body {body_pct:.2f}% — no rule matched"
    for p in priority:
        ok, why = results[p]           # correct unpack
        if ok:
            final_type, final_reason = p, why
            break

    comparison = []
    for p in priority:
        ok, why = results[p]           # correct unpack
        if p != final_type:
            comparison.append(f"- Not {p}: {why}")

    dbg = dict(o=o, h=h, l=l, c=c, range=rng, body=body, upper=upper, lower=lower,
               body_pct=body_pct, wick_ratio=wick_ratio)

    return {"final": (final_type, final_reason), "comparison": comparison, "dbg": dbg}

# ---------- Run ----------
if st.button("Analyze"):
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        st.error("No input.")
    else:
        for i, line in enumerate(lines, 1):
            parsed = parse_line(line)
            if not parsed:
                st.subheader(f"Candle {i}")
                st.caption(line)
                st.write("**Type:** Invalid Candle")
                st.write("**Reason:** Could not parse 4 numbers (O,H,L,C).")
                st.write("---")
                continue
            o,h,l,c,orig = parsed
            rep = classify(o,h,l,c)
            t, why = rep["final"]
            st.subheader(f"Candle {i}")
            st.caption(orig)
            st.write(f"**Type:** {t}")
            st.write(f"**Reason:** {why}")
            st.write("**Comparison:**")
            for row in rep["comparison"]:
                st.write(row)
            if show_debug:
                st.write("**Debug:**", rep["dbg"])
            st.write("---")
