"""Asks an AI (Groq) to write the summary. Falls back to the rule-based
summary if anything goes wrong, so the report always gets made.

Setup (once):
  1. pip install groq
  2. Create a free key at https://console.groq.com/keys
  3. In your terminal:  export GROQ_API_KEY="your-key-here"
"""
import os

from report import percent_change
from summary import rule_based_summary

# If Groq says this model doesn't exist or isn't allowed, pick another one from
# the models list in your Groq console and change this (or set GROQ_MODEL).
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def _pct(new, old):
    """Format a percent change for the prompt, or say there is no comparison."""
    change = percent_change(new, old)
    return "no comparison available" if change is None else f"{change:+.1f}%"


def build_prompt(this_week, last_week):
    """Put the facts and the instructions into one message for the AI."""
    products = ", ".join(f"{name} (${amount:,.2f})" for name, amount in this_week["top_products"])
    return (
        "You write the weekly sales summary for a busy small-business owner.\n"
        "Write 3 or 4 plain-English sentences. Use ONLY the facts below. "
        "Do not guess at reasons or causes, and do not mention anything that is not in the facts. "
        "No bullet points, no formatting.\n\n"
        "FACTS:\n"
        f"- Revenue this week: ${this_week['revenue']:,.2f} "
        f"({_pct(this_week['revenue'], last_week['revenue'])} vs last week)\n"
        f"- Orders: {this_week['order_count']} "
        f"({_pct(this_week['order_count'], last_week['order_count'])} vs last week)\n"
        f"- Average order value: ${this_week['average_order']:,.2f} "
        f"({_pct(this_week['average_order'], last_week['average_order'])} vs last week)\n"
        f"- Top products by revenue: {products}\n"
    )


def groq_summary(this_week, last_week):
    """Send the prompt to Groq and return the text it writes back."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    from groq import Groq  # imported here so the rest works even without the package

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": build_prompt(this_week, last_week)}],
        temperature=0.3,  # lower = more predictable, less creative
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("the AI returned an empty answer")
    return text


def ai_summary_with_fallback(this_week, last_week):
    """Try the AI first. If anything fails, use the rule-based summary instead."""
    try:
        return groq_summary(this_week, last_week)
    except Exception as error:  # a wide net on purpose: any failure -> fallback
        print(f"(AI summary unavailable: {error}. Using the rule-based summary.)")
        return rule_based_summary(this_week, last_week)
