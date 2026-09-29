# penaltyblog × Football Charts

A runnable example of [penaltyblog](https://github.com/martineastwood/penaltyblog)'s Dixon-Coles model on a league football-data.co.uk does not cover: Germany's **3. Liga**, loaded from the free [Football Charts API](https://www.football-charts.com/developers).

| File | What it is |
|---|---|
| `fc_3liga_dixon_coles.ipynb` | the notebook: load → check → walk-forward evaluation (RPS vs a baseline) |
| `fc_loader.py` | ~60-line loader returning penaltyblog's `FootballData` column layout (`date`, `team_home`, `team_away`, `goals_home`, `goals_away`, `fthg`, `ftag`, `hthg`, `htag`) |
| `build_notebook.py` | regenerates the notebook from source |

```bash
pip install "penaltyblog>=1.12.3" pandas requests jupyter
jupyter notebook fc_3liga_dixon_coles.ipynb
```

No key is needed for the current and previous season (300 requests/day per IP); set `FC_API_KEY` for 5,000/day with a free key from football-charts.com/developers. Older seasons need a paid key. Results only; this endpoint carries no odds.

Tested with penaltyblog 1.12.3, pandas 3.0.6, numpy 2.5.3. With pandas 3, use penaltyblog ≥ 1.12.3 (earlier versions raise `ValueError: buffer source array is read-only`; fixed in [#47](https://github.com/martineastwood/penaltyblog/issues/47)).

Data by [football-charts.com](https://www.football-charts.com).
