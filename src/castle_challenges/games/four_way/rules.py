"""Scoring rules for the four-way battle game."""

from ...common.allocation import Allocation, VALUES, validate

PAYOUTS = (9.0, 4.0, 2.0, 0.0)


def castle_points(players: tuple[Allocation, ...]) -> tuple[float, ...]:
    """Split each castle's points equally among all players tied for its lead."""
    if not players:
        raise ValueError("at least one player is required")
    for player in players:
        validate(player)
    totals = [0.0] * len(players)
    for castle, value in enumerate(VALUES):
        high = max(player[castle] for player in players)
        winners = [i for i, player in enumerate(players) if player[castle] == high]
        for i in winners:
            totals[i] += value / len(winners)
    return tuple(totals)


def payout(players: tuple[Allocation, Allocation, Allocation, Allocation]) -> tuple[float, ...]:
    """Return rank payouts; tied players average the payout slots they occupy."""
    if len(players) != 4:
        raise ValueError("four-way game requires exactly four players")
    scores = castle_points(players)
    order = sorted(range(4), key=lambda i: scores[i], reverse=True)
    result = [0.0] * 4
    start = 0
    while start < 4:
        end = start + 1
        while end < 4 and scores[order[end]] == scores[order[start]]:
            end += 1
        shared = sum(PAYOUTS[start:end]) / (end - start)
        for position in range(start, end):
            result[order[position]] = shared
        start = end
    return tuple(result)
