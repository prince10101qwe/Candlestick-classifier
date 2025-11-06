import streamlit as st
import re

st.title("Candlestick Identifier — Strict Rule Engine")

st.markdown("Paste your OHLC data below (any format, e.g. `O3,743.520 H3,745.840 L3,739.345 C3,745.240`):")
user_input = st.text_area("Input OHLC lines", height=200)

# --- Clean OHLC lines ---
def parse_input(text):
    candles = []
    for line in text.splitlines():
        nums = re.findall(r"[-+]?\d*\.?\d+", line.replace(",", ""))
        if len(nums) == 4:
            o, h, l, c = map(float, nums)
            candles.append((o, h, l, c))
    return candles

# --- Candle classification per updated rules ---
def classify(o, h, l, c):
    total = h - l if h != l else 0.0001
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    body_pct = (body / total) * 100

    result, reason, comp = "", "", []

    # ---- 1. DOJI ----
    if body_pct <= 10 and abs(upper - lower) <= 0.2 * max(upper, lower, 0.0001):
        result = "Doji"
        reason = f"Body tiny ({body_pct:.1f}%), wicks roughly equal (≤20% diff)"
        comp = [
            "- Not Bullish/Bearish Doji: no clear directional wick dominance",
            "- Not Pin Bar: wicks not 2× body",
            "- Not Long Wick Rejection: wick ratio not 4× smaller"
        ]

    # ---- 2. Bullish Doji (Dragonfly) ----
    elif body_pct <= 10 and lower >= 2 * body and (upper <= 0.1 * lower or upper == 0):
        result = "Bullish Doji (Dragonfly)"
        reason = f"Body tiny ({body_pct:.1f}%), long lower wick ≥2× body, upper wick ≤10% of lower wick"
        comp = [
            "- Not Doji: wick lengths not equal",
            "- Not Pin Bar: body% ≤10%",
            "- Not Long Wick Rejection: upper wick ratio >¼ lower wick not valid"
        ]

    # ---- 3. Bearish Doji (Gravestone) ----
    elif body_pct <= 10 and upper >= 2 * body and (lower <= 0.1 * upper or lower == 0):
        result = "Bearish Doji (Gravestone)"
        reason = f"Body tiny ({body_pct:.1f}%), long upper wick ≥2× body, lower wick ≤10% of upper wick"
        comp = [
            "- Not Doji: wick lengths not equal",
            "- Not Pin Bar: body% ≤10%",
            "- Not Long Wick Rejection: lower wick ratio >¼ upper wick not valid"
        ]

    # ---- 4. Bullish Pin Bar ----
    elif body_pct < 20 and lower >= 2 * body and upper <= body:
        result = "Bullish Pin Bar"
        reason = f"Body small ({body_pct:.1f}%), long lower wick ≥2× body, upper wick ≤ body"
        comp = [
            "- Not Doji: body% >10%",
            "- Not Long Wick Rejection: upper wick not ≤¼ lower wick",
            "- Not Spinning Top: wicks not equal"
        ]
        # convert pin bar to long wick rejection if lower wick > body and all rules valid
        if lower > body:
            result = "Bullish Long Wick Rejection"
            reason = f"Body ({body_pct:.1f}%), long lower wick > body (≥2×), upper wick ≤¼ lower wick (converted from pin bar)"
            comp = [
                "- Converted: wick longer than body",
                "- Weaker than Bullish Pin Bar"
            ]

    # ---- 5. Bearish Pin Bar ----
    elif body_pct < 20 and upper >= 2 * body and lower <= body:
        result = "Bearish Pin Bar"
        reason = f"Body small ({body_pct:.1f}%), long upper wick ≥2× body, lower wick ≤ body"
        comp = [
            "- Not Doji: body% >10%",
            "- Not Long Wick Rejection: lower wick not ≤¼ upper wick",
            "- Not Spinning Top: wicks not equal"
        ]
        if upper > body:
            result = "Bearish Long Wick Rejection"
            reason = f"Body ({body_pct:.1f}%), long upper wick > body (≥2×), lower wick ≤¼ upper wick (converted from pin bar)"
            comp = [
                "- Converted: wick longer than body",
                "- Weaker than Bearish Pin Bar"
            ]

    # ---- 6. Bullish Long Wick Rejection ----
    elif body_pct <= 30 and lower >= 2 * body and upper <= lower / 4:
        result = "Bullish Long Wick Rejection"
        reason = f"Body ({body_pct:.1f}%), long lower wick ≥2× body, upper wick ≤¼ lower wick"
        comp = [
            "- Not Doji: body% >10%",
            "- Not Pin Bar: upper wick too small",
            "- Not Spinning Top: wicks not equal"
        ]

    # ---- 7. Bearish Long Wick Rejection ----
    elif body_pct <= 30 and upper >= 2 * body and lower <= upper / 4:
        result = "Bearish Long Wick Rejection"
        reason = f"Body ({body_pct:.1f}%), long upper wick ≥2× body, lower wick ≤¼ upper wick"
        comp = [
            "- Not Doji: body% >10%",
            "- Not Pin Bar: lower wick too small",
            "- Not Spinning Top: wicks not equal"
        ]

    # ---- 8. Spinning Top ----
    elif 10 <= body_pct <= 30 and (upper >= body or lower >= body) and abs(upper - lower) <= 0.4 * max(upper, lower, 0.0001):
        result = "Spinning Top"
        reason = f"Body ({body_pct:.1f}%), both wicks ≥ body, roughly equal (≤40% diff)"
        comp = [
            "- Not Doji: body% >10%",
            "- Not Pin Bar: wicks not 2× body",
            "- Not Long Wick Rejection: wick ratio not 4× smaller"
        ]

    else:
        result = "Normal Candle"
        reason = f"Body {body_pct:.1f}%, wick proportions do not match any pattern"
        comp = [
            "- Not Doji: body% >10% or wicks unequal",
            "- Not Pin Bar or Rejection: wick/body ratio mismatch",
            "- Not Spinning Top: wicks unequal"
        ]

    return result, reason, comp

candles = parse_input(user_input)

if st.button("Analyze"):
    if not candles:
        st.error("No valid OHLC data found.")
    else:
        for i, (o, h, l, c) in enumerate(candles, start=1):
            result, reason, comp = classify(o, h, l, c)
            st.subheader(f"Candle {i}")
            st.write(f"**Candle Type:** {result}")
            st.write(f"**Reason:** {reason}")
            st.write("**Comparison:**")
            for line in comp:
                st.write(line)
