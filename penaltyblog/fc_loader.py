"""
Load Football Charts match results into the column layout penaltyblog uses.

Football Charts (https://www.football-charts.com) publishes results, half-time
scores and goal minutes for 90+ leagues, including lower divisions and women's
leagues that football-data.co.uk does not cover. The API is free for the
current and previous season: 300 requests/day without a key, 5,000/day with a
free key from https://www.football-charts.com/developers. Older seasons (back
to 2020) need a paid key. Results only: this endpoint carries no odds.

Attribution is required: "Data by football-charts.com".

    from fc_loader import fc_results, fc_leagues
    df = fc_results("germany3", ["2025-2026", "2026-2027"])

Columns match penaltyblog.scrapers.FootballData where they overlap:
date, season, competition, team_home, team_away, goals_home, goals_away,
fthg, ftag, hthg, htag, plus first_goal_minute.
"""
import os
import re

import pandas as pd
import requests

API = "https://footballcharts-backend.onrender.com/api/v1"


def _get(path, params=None, api_key=None):
    key = api_key or os.environ.get("FC_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = requests.get(f"{API}{path}", params=params, headers=headers, timeout=30)
    if r.status_code == 403:
        raise PermissionError(
            f"{path} {params}: this season needs a paid key "
            "(free tier = current and previous season).")
    r.raise_for_status()
    return r.json()


def fc_leagues(api_key=None):
    """All leagues with their codes and the seasons your key can read."""
    data = _get("/leagues/", api_key=api_key)
    return pd.DataFrame(data["leagues"])[["league", "name", "country", "seasons"]]


def _score(s):
    m = re.match(r"^\s*(\d+)\s*[:\-]\s*(\d+)\s*$", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def fc_results(league, seasons, api_key=None):
    """Finished matches for `league` in each of `seasons` ("2025-2026" style,
    or "2026" for calendar-year leagues), sorted by date."""
    if isinstance(seasons, str):
        seasons = [seasons]
    rows = []
    for season in seasons:
        data = _get(f"/leagues/{league}/results/", {"season": season}, api_key)
        for m in data["matches"]:
            fthg, ftag = _score(m.get("score"))
            if fthg is None:          # abandoned / not yet played
                continue
            hthg, htag = _score(m.get("ht_result"))
            rows.append({
                "date": pd.to_datetime(m["date"]),
                "season": season,
                "competition": league,
                "team_home": m["homeTeam"],
                "team_away": m["awayTeam"],
                "goals_home": fthg,
                "goals_away": ftag,
                "fthg": fthg,
                "ftag": ftag,
                "hthg": hthg,
                "htag": htag,
                "first_goal_minute": m.get("first_goal_time"),
            })
    df = pd.DataFrame(rows).sort_values(["date", "team_home"]).reset_index(drop=True)
    # Same index style as penaltyblog's FootballData scraper.
    df.index = [f"{int(d.timestamp())}---{_slug(h)}---{_slug(a)}"
                for d, h, a in zip(df["date"], df["team_home"], df["team_away"])]
    df.index.name = "id"
    df.attrs["attribution"] = "Data by football-charts.com"
    return df
