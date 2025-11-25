import streamlit as st
import re

st.set_page_config(page_title="Candlestick Identifier — Final Rules", layout="centered")
st.title("Candlestick Identifier — FINAL UPDATED RULES (FULL LOGIC)")

raw = st.text_area("Paste OHLC lines:", height=180)
show_debug = st.checkbox("Show debug metrics")

# ===============================================================
#               CLEAN PARSER (RELIABLE)
# ===============================================================
def parse_line(line):
    s = line.strip()
    # capture full numbers including thousands commas
    nums = re.findall(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", s)
    nums = [float(x.replace(",", "")) for x in nums]
    if len(nums) >= 4:
        o, h, l, c = nums[:4]
        return o, h, l, c, line.strip()
    return None

# ===============================================================
#               BODY POSITION CHECK
# ===============================================================
def body_top(body_high, high, rng, pct):
    return body_high >= (high - rng * pct)

def body_bottom(body_low, low, rng, pct):
    return body_low <= (low + rng * pct)

# ===============================================================
#               MAIN CLASSIFICATION
# ===============================================================
def classify(o, h, l, c):
    # INVALID CHECKS
    if l >= h:
        return {"final": ("Invalid Candle", "LOW ≥ HIGH"), "comparison": [], "dbg": {}}

    rng = h - l
    if rng < 1e-9:
        return {"final": ("Invalid Candle", "Range too small"), "comparison": [], "dbg": {}}

    body = abs(c - o)
    body_pct = (body / rng) * 100
    upper = h - max(o, c)
    lower = min(o, c) - l

    body_high = max(o, c)
    body_low = min(o, c)

    # wick ratio
    eps = 1e-12
    wick_ratio = max(upper, lower) / max(min(upper, lower), eps)

    results = {}

    # ===============================================================
    # 1. STANDARD DOJI
    # ===============================================================
    results["Doji"] = (
        body_pct <= 10 and
        upper >= body and
        lower >= body and
        abs(upper - lower) <= 0.20 * max(upper, lower),
        f"body {body_pct:.2f}%, wick symmetry {abs(upper-lower):.4f} ≤ 20%"
    )

    # ===============================================================
    # 2. BULLISH DOJI (DRAGONFLY)
    # ===============================================================
    results["Bullish Doji (Dragonfly)"] = (
        body_pct <= 10 and
        body_top(body_high, h, rng, 0.10) and
        lower >= 2 * body and
        upper <= 0.10 * lower,
        f"body {body_pct:.2f}%, lower≥2×body, upper≤10% of lower"
    )

    # ===============================================================
    # 3. BEARISH DOJI (GRAVESTONE)
    # ===============================================================
    results["Bearish Doji (Gravestone)"] = (
        body_pct <= 10 and
        body_bottom(body_low, l, rng, 0.10) and
        upper >= 2 * body and
        lower <= 0.10 * upper,
        f"body {body_pct:.2f}%, upper≥2×body, lower≤10% of upper"
    )

    # ===============================================================
    # 4. BULLISH PIN BAR
    # ===============================================================
    results["Bullish Pin Bar"] = (
        body_pct <= 20 and
        body_top(body_high, h, rng, 0.20) and
        lower >= 2 * body and
        upper <= body,
        f"body {body_pct:.2f}%, body near top20%, lower≥2×body, upper≤body"
    )

    # ===============================================================
    # 5. BEARISH PIN BAR
    # ===============================================================
    results["Bearish Pin Bar"] = (
        body_pct <= 20 and
        body_bottom(body_low, l, rng, 0.20) and
        upper >= 2 * body and
        lower <= body,
        f"body {body_pct:.2f}%, body near bottom20%, upper≥2×body, lower≤body"
    )

    # ===============================================================
    # 6. BULLISH LONG WICK REJECTION
    # ===============================================================
    results["Bullish Long Wick Rejection"] = (
        body_pct <= 30 and
        body_top(body_high, h, rng, 0.30) and
        lower >= 2 * body and
        upper <= 0.26 * lower,
        f"body {body_pct:.2f}%, body top30%, lower≥2×body, upper≤0.26×lower"
    )

    # ===============================================================
    # 7. BEARISH LONG WICK REJECTION
    # ===============================================================
    results["Bearish Long Wick Rejection"] = (
        body_pct <= 30 and
        body_bottom(body_low, l, rng, 0.30) and
        upper >= 2 * body and
        lower <= 0.26 * upper,
        f"body {body_pct:.2f}%, body bottom30%, upper≥2×body, lower≤0.26×upper"
    )

    # ===============================================================
    # 8. SPINNING TOP
    # ===============================================================
    results["Spinning Top"] = (
        body_pct <= 30 and
        upper >= body and
        lower >= body and
        abs(upper - lower) <= 0.40 * max(upper, lower),
        f"body {body_pct:.2f}%, both wicks≥body, wick symmetry≤40%"
    )

    # ===============================================================
    # 9. STRONG CANDLE
    # ===============================================================
    strong = False
    if body >= 0.85 * rng and (upper + lower <= 0.15 * rng or (upper <= 0.075 * rng and lower <= 0.075 * rng)):
        strong = True

    if strong:
        t = "Strong Candle (Bullish)" if c > o else "Strong Candle (Bearish)"
        results[t] = (True, f"body {body_pct:.2f}% ≥85%, wicks small")

    # ===============================================================
    # TIE-BREAK PRIORITY
    # ===============================================================
    priority = [
        "Bullish Pin Bar",
        "Bearish Pin Bar",
        "Bullish Long Wick Rejection",
        "Bearish Long Wick Rejection",
        "Doji",
        "Bullish Doji (Dragonfly)",
        "Bearish Doji (Gravestone)",
        "Spinning Top",
        "Strong Candle (Bullish)",
        "Strong Candle (Bearish)"
    ]

    final_type = "Normal Candlestick"
    final_reason = "Does not match any rule."

    for name in priority:
        if name in results:
            ok, why = results[name]
            if ok:
                final_type = name
                final_reason = why
                break

    comparison = []
    for name in priority:
        if name not in results:
            continue
        ok, why = results[name]
        if name != final_type:
            comparison.append(f"- Not {name}: {why}")

    dbg = {
        "O": o, "H": h, "L": l, "C": c,
        "range": rng, "body": body,
        "upper": upper, "lower": lower,
        "body%": body_pct,
        "wick_ratio": wick_ratio,
    }

    return {"final": (final_type, final_reason), "comparison": comparison, "dbg": dbg}


# ===============================================================
#               EXECUTION
# ===============================================================
if st.button("Analyze"):
    for i, line in enumerate(raw.splitlines(), start=1):
        parsed = parse_line(line)
        st.subheader(f"Candle {i}")
        st.caption(line.strip())

        if not parsed:
            st.write("Invalid Input: Could not parse OHLC.")
            st.write("---")
            continue

        o, h, l, c, rawline = parsed
        rep = classify(o, h, l, c)

        t, reason = rep["final"]
        st.write(f"**Type:** {t}")
        st.write(f"**Reason:** {reason}")

        st.write("**Comparison:**")
        for row in rep["comparison"]:
            st.write(row)

        if show_debug:
            st.write("**Debug:**", rep["dbg"])

        st.write("---")
