"""Turns the report numbers into a plain-English summary, using simple rules.

No AI and no API key needed. Later, you can write another function with the
same inputs (this_week, last_week) that asks an AI instead, and swap it in.
"""
from report import percent_change


def describe_change(change):
    """Turn a percent change into a phrase. 'change' is a number or None."""
    if change is None:
        return None
    if change >= 10:
        return f"up strongly ({change:+.1f}%)"
    if change >= 2:
        return f"up slightly ({change:+.1f}%)"
    if change > -2:
        return f"about flat ({change:+.1f}%)"
    if change > -10:
        return f"down slightly ({change:+.1f}%)"
    return f"down sharply ({change:+.1f}%)"


def rule_based_summary(this_week, last_week):
    """Write a short summary from two dictionaries made by summarize()."""
    sentences = []

    # 1. Headline: how did revenue do?
    revenue_change = percent_change(this_week["revenue"], last_week["revenue"])
    phrase = describe_change(revenue_change)
    if phrase is None:
        sentences.append(
            f"Revenue was ${this_week['revenue']:,.2f}. "
            "There is no data for last week, so there is nothing to compare it with."
        )
    else:
        sentences.append(f"Revenue was ${this_week['revenue']:,.2f}, {phrase} vs last week.")

        # 2. Why? More orders, or bigger orders? Whichever moved more is the driver.
        order_change = percent_change(this_week["order_count"], last_week["order_count"])
        avg_change = percent_change(this_week["average_order"], last_week["average_order"])
        if order_change is not None and avg_change is not None and abs(revenue_change) >= 2:
            if abs(order_change) >= abs(avg_change):
                driver = f"order volume ({order_change:+.1f}%)"
            else:
                driver = f"average order value ({avg_change:+.1f}%)"
            sentences.append(f"The biggest factor was {driver}.")

    # 3. Best seller, and its share of the week's revenue
    if this_week["top_products"] and this_week["revenue"] > 0:
        name, amount = this_week["top_products"][0]
        share = amount / this_week["revenue"] * 100
        sentences.append(f"{name} was the top seller with ${amount:,.2f} ({share:.0f}% of revenue).")

        # 4. Did the best seller change since last week?
        if last_week["top_products"]:
            last_name = last_week["top_products"][0][0]
            if last_name != name:
                sentences.append(f"Last week's top seller was {last_name}.")

    return " ".join(sentences)
