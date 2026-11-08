# betting-data

Picks, prices and results for the daily football analysis. Public data only: no account details.

- `picks.json`: the data (see `SCHEMA.md`)
- `SCHEMA.md`: field list and the rules for editing

History loaded: Oct 31 to Nov 3 2026 from the Excel tracker (106 single-game picks, 7 slips).

## Independent side models

`models_sim.py` reads `picks.json` and `league_base_rates.json` and writes `models_sim.json`: chances of Under 2.5 and Under 3.5 from several simple models, scored on finished games. It is data collection only. Nothing in it feeds any pick, slip, record or track, and the dashboard's other tabs never read it. Re-run it after each grading pass: `python3 models_sim.py`.
