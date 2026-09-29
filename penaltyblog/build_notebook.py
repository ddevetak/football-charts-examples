"""Builds fc_3liga_dixon_coles.ipynb (run once; the notebook is the artefact)."""
import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
md("""# 3. Liga with penaltyblog: Dixon-Coles on Football Charts data

[football-data.co.uk](https://football-data.co.uk/germanym.php) covers the Bundesliga and 2. Bundesliga. For Germany's third tier, and for many other lower divisions and women's leagues, this notebook uses the **Football Charts API** instead and fits penaltyblog's Dixon-Coles model to it.

What it shows:
1. loading results into the same columns penaltyblog's `FootballData` scraper returns;
2. checking the data before modelling;
3. a **walk-forward** evaluation: every match is predicted using only matches played before it, and scored with the ranked probability score (RPS) against a naive baseline.

*Disclosure: written by the maintainer of Football Charts. The API is free for the current and previous season (300 requests/day without a key, 5,000/day with a free key from [football-charts.com/developers](https://www.football-charts.com/developers)); older seasons need a paid key. This endpoint has results only, no odds. Data by football-charts.com.*"""),

code("""import numpy as np
import pandas as pd
import penaltyblog as pb
from fc_loader import fc_leagues, fc_results

print("penaltyblog", pb.__version__)   # needs >= 1.12.3 with pandas 3"""),

md("""## 1. Load

`fc_leagues()` lists every league code and the seasons your key can read. 3. Liga is `germany3`."""),

code("""leagues = fc_leagues()
print(len(leagues), "leagues")
leagues[leagues.country == "Germany"]"""),

code("""df = fc_results("germany3", ["2025-2026", "2026-2027"])
print(len(df), "matches;", df.season.value_counts().to_dict())
df.head()"""),

md("""## 2. Check before modelling

A completed 20-team season should have exactly 38 matches per team and no duplicate fixtures."""),

code("""done = df[df.season == "2025-2026"]
per_team = pd.concat([done.team_home, done.team_away]).value_counts()
assert len(per_team) == 20 and (per_team == 38).all(), per_team
assert not df.index.duplicated().any()
assert (df[["goals_home", "goals_away"]] >= 0).all().all()

new_teams = sorted(set(df[df.season == "2026-2027"][["team_home", "team_away"]].values.ravel()) - set(per_team.index))
print("2025-26: 20 teams x 38 matches, no duplicates")
print("new in 2026-27 (promoted/relegated):", new_teams)
print("home/draw/away 2025-26:",
      (np.sign(done.goals_home - done.goals_away).value_counts(normalize=True)
       .rename({1: "home", 0: "draw", -1: "away"}).round(3).to_dict()))"""),

md("""## 3. Walk-forward evaluation

For each match day from January 2026 onwards: fit Dixon-Coles on every earlier match (time-decayed with `dixon_coles_weights`, penaltyblog's default ξ = 0.0018/day), predict that day's matches, then score the home/draw/away probabilities with RPS (lower is better).

Baseline: the home/draw/away frequencies of the same training data, so the model has to beat "no team information".

A newly promoted or relegated team cannot be rated until it has played. Matches involving a team with fewer than 3 earlier matches are skipped and counted, not silently dropped."""),

code("""def outcome(h, a):
    return 0 if h > a else (1 if h == a else 2)   # home, draw, away

MIN_GAMES = 3
eval_days = sorted(df.loc[df.date >= "2026-01-01", "date"].unique())
rows, skipped = [], 0

for day in eval_days:
    train = df[df.date < day]
    games = pd.concat([train.team_home, train.team_away]).value_counts()
    weights = pb.models.dixon_coles_weights(train.date, xi=0.0018, base_date=day)
    model = pb.models.DixonColesGoalModel(
        train.goals_home, train.goals_away, train.team_home, train.team_away, weights)
    model.fit()
    base = (np.bincount([outcome(h, a) for h, a in zip(train.goals_home, train.goals_away)],
                        minlength=3) / len(train))
    for _, m in df[df.date == day].iterrows():
        if games.get(m.team_home, 0) < MIN_GAMES or games.get(m.team_away, 0) < MIN_GAMES:
            skipped += 1
            continue
        grid = model.predict(m.team_home, m.team_away)
        rows.append({
            "date": day, "season": m.season,
            "home": m.team_home, "away": m.team_away,
            "p_home": grid.home_win, "p_draw": grid.draw, "p_away": grid.away_win,
            "result": outcome(m.goals_home, m.goals_away),
            "base": base,
        })

pred = pd.DataFrame(rows)
print(f"{len(pred)} matches predicted, {skipped} skipped (team with < {MIN_GAMES} earlier matches)")"""),

code("""def rps(probs, results):
    return np.mean([pb.metrics.rps_average([p], [r]) for p, r in zip(probs, results)])

model_probs = pred[["p_home", "p_draw", "p_away"]].values
summary = []
for label, part in [("all", pred), *pred.groupby("season")]:
    idx = part.index
    summary.append({
        "matches": label, "n": len(part),
        "RPS Dixon-Coles": rps(model_probs[idx], part.result),
        "RPS baseline": rps(np.stack(part.base.values), part.result),
    })
summary = pd.DataFrame(summary).set_index("matches")
summary["improvement %"] = 100 * (1 - summary["RPS Dixon-Coles"] / summary["RPS baseline"])
summary.round(4)"""),

md("""**Reading the table.** RPS runs from 0 (perfect) upwards; for three-way football outcomes the practical range is narrow, so a few percent is a real difference. On the complete 2025-26 matches the model beats the no-information baseline clearly. Early in 2026-27 it does not: six teams are new to the division and every team has only a handful of matches, so the ratings are still mostly last season's. That is the expected behaviour of a team-strength model at the start of a season, not a bug, and it is why the evaluation reports each season separately. The numbers change as the season is played; re-run to update."""),

md("""## 4. A look at the predictions

The model's favourite in each predicted match, and how often the favourite won, by confidence band. A well-calibrated model's hit rate should rise with its confidence."""),

code("""pred["fav_p"] = model_probs.max(axis=1)
pred["fav_won"] = model_probs.argmax(axis=1) == pred.result
bands = pd.cut(pred.fav_p, [0, 0.45, 0.55, 1.0], labels=["< 45%", "45-55%", "> 55%"])
pred.groupby(bands, observed=True).agg(matches=("fav_won", "size"),
                                       mean_confidence=("fav_p", "mean"),
                                       hit_rate=("fav_won", "mean")).round(3)"""),

md("""## Notes and next steps

* **One league, small sample.** 3. Liga has many drawn, low-margin games; a few hundred predictions is enough to compare against a baseline, not to rank models. Treat the numbers as a sanity check.
* **Promoted/relegated teams** carry no rating at the start of a season. Extending training data backwards (earlier 3. Liga seasons, or the team's previous division) fixes that; seasons before the previous one need a paid key.
* **Same code, other leagues:** swap `"germany3"` for any code in `fc_leagues()`, e.g. `"national"` (English National League), `"sweden2"` (Superettan) or `"wgermany1"` (Frauen-Bundesliga).
* The results carry half-time scores (`hthg`, `htag`) and the first goal minute, so half-time and goal-timing models work with the same loader.

Data by [football-charts.com](https://www.football-charts.com). Model: [penaltyblog](https://github.com/martineastwood/penaltyblog) by Martin Eastwood."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python"}})
nbf.write(nb, "fc_3liga_dixon_coles.ipynb")
print("written")
