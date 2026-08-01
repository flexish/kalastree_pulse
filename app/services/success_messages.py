"""
Motivational messages shown on the reflection success screen.

Picked at random rather than deterministically like the daily quote — this
is a one-time celebratory moment, not something a user checks back on.
Tiered by rating so a rough day gets encouragement, not forced enthusiasm.
"""

import random

LOW_TIER = (
    "Tough days are part of building something real. Tomorrow's a fresh shot.",
    "Showing up honestly today matters more than the number.",
    "Every company has days like this. What matters is you named it.",
)

MID_TIER = (
    "Steady progress adds up. Keep going.",
    "That's real movement — small steps still count.",
    "Consistency beats intensity. Nice work today.",
)

HIGH_TIER = (
    "That's a great day for Kalastree. Well done.",
    "Momentum like this is how the mission gets closer.",
    "Huge day — the tree felt that one.",
)


def get_success_message(rating: int) -> str:
    if rating <= 3:
        tier = LOW_TIER
    elif rating <= 7:
        tier = MID_TIER
    else:
        tier = HIGH_TIER
    return random.choice(tier)
