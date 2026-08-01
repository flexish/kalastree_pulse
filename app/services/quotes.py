"""
Daily motivational quote.

A small curated set, rotated deterministically by day of year so everyone
sees the same quote on a given day. Unlike mission targets, this isn't a
company-goal value an admin needs to edit, so it lives in code rather than
configuration.
"""

from datetime import date
from typing import NamedTuple


class Quote(NamedTuple):
    text: str
    author: str


QUOTES: tuple[Quote, ...] = (
    Quote("Small improvements every day create extraordinary companies.", "Kalastree Pulse"),
    Quote("Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln"),
    Quote("Progress, not perfection.", "Kalastree Pulse"),
    Quote("The secret of getting ahead is getting started.", "Mark Twain"),
    Quote("Well done is better than well said.", "Benjamin Franklin"),
    Quote("Focus on being productive instead of busy.", "Tim Ferriss"),
    Quote("Great things are done by a series of small things brought together.", "Vincent Van Gogh"),
    Quote("Action is the foundational key to all success.", "Pablo Picasso"),
    Quote("A goal without a plan is just a wish.", "Antoine de Saint-Exupéry"),
    Quote("Consistency is what transforms average into excellence.", "Kalastree Pulse"),
)


def get_daily_quote(today: date | None = None) -> Quote:
    today = today or date.today()
    return QUOTES[today.timetuple().tm_yday % len(QUOTES)]
