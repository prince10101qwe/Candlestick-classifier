import streamlit as st
import re

st.title("Candlestick Type Identifier (with Reasoning & Comparison)")

st.markdown("Paste your OHLC data below (any format):")
user_input = st.text_area("Example: O3,743.520 H3,745.840 L3,739.345 C3,745.240", height=200)

# --- Clean and extract OHLC ---
def parse_input(text):
    candles = []
    for line in text.splitlines():
        nums = re.findall(r"[-+]?\d*\.?\d+", line.replace(",", ""))
        if len(nums) == 4:
            o, h, l, c = map(float, nums)
            candles.append((o, h, l, c))
    return candles

def classify(o, h, l, c):
    total_range = h - l if h != l else 0.0001
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    body_pct = (body / total_range) * 100
    result, reason, comparison = "", "", []

    # --- Doji / Bullish Doji / Bearish Doji ---
    if body_pct <= 10 and abs(upper - lower) <= 0.2 * max(upper, lower, 0.0001):
        if c > o:
            result = "Bullish Doji"
        elif c < o:
            result = "Bearish Doji"
        else:
            result = "Neutral Doji"
        reason = f"Body very small ({body_pct:.1f}%), wicks roughly equal"
        comparison = [
            "- Not Pin Bar: wicks not 2× body",
            "- Not Long Wick Rejection: wick ratio not 4× smaller",
            "- Not Spinning Top: body% too low (<10%)"
        ]

    # --- Bullish Pin Bar ---
    elif body_pct < 20 and lower >= 2 * body and upper <= body:
        result = "Bullish Pin Bar"
        reason = f"Body small ({body_pct:.1f}%), long lower wick >2× body, upper wick ≤ body"
        comparison = [
            "- Not Doji: body% >10%",
            "- Not Long Wick Rejection: upper wick not 4× smaller",
            "- Not Spinning Top: wicks not equal"
        ]

    # --- Bearish Pin Bar ---
    elif body_pct < 20 and upper >= 2 * body and lower <= body:
        result = "Bearish Pin Bar"
        reason = f"Body small ({body_pct:.1f}%), long upper wick >2× body, lower wick ≤ body"
        comparison = [
            "- Not Doji: body% >10%",
            "- Not Long Wick Rejection: lower wick not 4× smaller",
            "- Not Spinning Top: wicks not equal"
        ]

    # --- Bullish Long Wick Rejection ---
    elif body_pct <= 30 and lower >= 2 * body and upper <= lower / 4:
        result = "Bullish Long Wick Rejection"
        reason = f"Body ({body_pct:.1f}%), long lower wick >2× body, upper wick ≤¼ lower wick"
        comparison = [
            "- Not Doji: body not ≈ close",
            "- Not Pin Bar: upper wick too small for Pin Bar",
            "- Not Spinning Top: wicks not equal"
        ]

    # --- Bearish Long Wick Rejection ---
    elif body_pct <= 30 and upper >= 2 * body and lower <= upper / 4:
        result = "Bearish Long Wick Rejection"
        reason = f"Body ({body_pct:.1f}%), long upper wick >2× body, lower wick ≤¼ upper wick"
        comparison = [
            "- Not Doji: body not ≈ close",
            "- Not Pin Bar: lower wick too small for Pin Bar",
            "- Not Spinning Top: wicks not equal"
        ]

    # --- Spinning Top ---
    elif 10 <= body_pct <= 30 and (upper >= body or lower >= body) and abs(upper - lower) <= 0.4 * max(upper, lower, 0.0001):
        result = "Spinning Top"
        reason = f"Body ({body_pct:.1f}%), both wicks roughly equal and ≥ body"
        comparison = [
            "- Not Doji: body% >10%",
            "- Not Pin Bar: wicks not 2× body",
            "- Not Long Wick Rejection: wicks too balanced"
        ]

    else:
        result = "Normal Candle"
        reason = f"Body {body_pct:.1f}%, wick proportions do not match any pattern"
        comparison = [
            "- Not Doji: body% >10%",
            "- Not Pin Bar or Rejection: wick/body ratio mismatch",
            "- Not Spinning Top: wicks unequal"
        ]

    return result, reason, comparison

candles = parse_input(user_input)
if st.button("Analyze"):
    if not candles:
        st.error("No valid OHLC data found.")
    else:
        for i, (o, h, l, c) in enumerate(candles, start=1):
            result, reason, comparison = classify(o, h, l, c)
            st.subheader(f"Candle {i}")
            st.write(f"Candle Type: {result}")
            st.write(f"Reason: {reason}")
            st.write("Comparison:")
            for line in comparison:
                st.write(line)
