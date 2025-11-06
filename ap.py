import streamlit as st
import re

st.set_page_config(page_title="Candlestick Identifier — Strict Rules", layout="centered")
st.title("Candlestick Identifier — Strict Rules + Input Validation")

raw = st.text_area("Paste OHLC lines (any format)", height=200)


# ---------------------- INPUT CLEANING ----------------------
def parse_input(text):
    candles = []
    for line in text.splitlines():
        nums = re.findall(r"[-+]?\d*\.?\d+", line.replace(",", ""))
        if len(nums) >= 4:
            o, h, l, c = map(float, nums[:4])
            candles.append((o, h, l, c, line.strip()))
    return candles


# ---------------------- CLASSIFICATION ----------------------
def classify(o, h, l, c):
    # ----------- INVALID CHECK: HIGH / LOW ORDER -----------
    if l >= h:
        return {
            "final": ("Invalid Candle", "LOW is greater than or equal to HIGH."),
            "comparison": ["All patterns skipped due to invalid OHLC."]
        }

    # ----------- INVALID CHECK: EXTREME VALUES -----------
    if max(abs(o), abs(h), abs(l), abs(c)) > 10_000_000:
        return {
            "final": ("Invalid Candle", "Input numbers extremely large (comma-format issue)."),
            "comparison": ["Detected unreasonable magnitude → likely formatting problem."]
        }

    total = h - l
    if total < 1e-9:
        return {
            "final": ("Invalid Candle", "Candle range too small."),
            "comparison": ["High and low are almost equal."]
        }

    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l

    body_pct = (body / total) * 100 if total > 0 else 999999

    # ----------- INVALID CHECK: BODY TOO LARGE -----------
    if body_pct > 500:
        return {
            "final": ("Invalid Candle", f"Body% {body_pct:.2f}% → corrupted OHLC."),
            "comparison": ["Range extremely small or numbers misformatted."]
        }

    # ---------- PATTERN MATCHING ----------
    eps = 1e-12
    wick_ratio = max(upper, lower) / max(min(upper, lower), eps)

    results = {}

    # 1) Doji
    results["Doji"] = (
        body_pct <= 10 and upper >= body and lower >= body and wick_ratio <= 1.2,
        f"body {body_pct:.2f}%, wick ratio {wick_ratio:.2f}"
    )

    # 2) Bullish Doji
    results["Bullish Doji (Dragonfly)"] = (
        body_pct <= 10 and lower >= 2*body and upper <= 0.1*lower,
        f"body {body_pct:.2f}%, lower {lower:.4g} ≥2×body, upper {upper:.4g} ≤10% of lower"
    )

    # 3) Bearish Doji
    results["Bearish Doji (Gravestone)"] = (
        body_pct <= 10 and upper >= 2*body and lower <= 0.1*upper,
        f"body {body_pct:.2f}%, upper {upper:.4g} ≥2×body, lower {lower:.4g} ≤10% of upper"
    )

    # 4) Bullish Pin Bar
    results["Bullish Pin Bar"] = (
        body_pct < 20 and lower >= 2*body and upper <= body,
        f"body {body_pct:.2f}%, lower ≥2×body, upper ≤ body"
    )

    # 5) Bearish Pin Bar
    results["Bearish Pin Bar"] = (
        body_pct < 20 and upper >= 2*body and lower <= body,
        f"body {body_pct:.2f}%, upper ≥2×body, lower ≤ body"
    )

    # 6) Bullish LWR
    results["Bullish Long Wick Rejection"] = (
        body_pct <= 30 and lower >= 2*body and upper <= 0.25*lower,
        f"body {body_pct:.2f}%, lower ≥2×body, upper ≤¼ lower"
    )

    # 7) Bearish LWR
    results["Bearish Long Wick Rejection"] = (
        body_pct <= 30 and upper >= 2*body and lower <= 0.25*upper,
        f"body {body_pct:.2f}%, upper ≥2×body, lower ≤¼ upper"
    )

    # 8) Spinning Top
    results["Spinning Top"] = (
        10 <= body_pct <= 30 and upper >= body and lower >= body and wick_ratio <= 1.4,
        f"body {body_pct:.2f}%, wicks ≥ body, wick ratio {wick_ratio:.2f}"
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

    final_type = "Normal Candle"
    final_reason = f"body {body_pct:.2f}% — no rule matched"

    for p in priority:
        ok, why in results[p]
        if ok:
            final_type = p
            final_reason = why
            break

    comparison = []
    for p in priority:
        ok, why in results[p]
        if p != final_type:
            comparison.append(f"- Not {p}: {why}")

    return {"final": (final_type, final_reason), "comparison": comparison}


# ---------------------- PROCESS ----------------------
candles = parse_input(raw)

if st.button("Analyze"):
    if not candles:
        st.error("No valid OHLC extracted.")
    else:
        for i, (o, h, l, c, line) in enumerate(candles, start=1):
            report = classify(o, h, l, c)
            t, why = report["final"]

            st.subheader(f"Candle {i}")
            st.caption(line)
            st.write(f"**Type:** {t}")
            st.write(f"**Reason:** {why}")
            st.write("**Comparison:**")
            for r in report["comparison"]:
                st.write(r)
            st.write("---")
