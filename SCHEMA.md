# picks.json schema (version 1)

The file is the source of truth. Excel and the dashboard are views of it.

## Rules
1. A pick is added once, before kickoff, with `logged_at` set (ISO 8601, America/New_York offset).
2. After that, a pick is only edited to add its result fields: `home_goals`, `away_goals`, `status`, `result`, `profit_units`, `closing_odds_american`, and `placed` or `stake_dollars` if the user tells us what he bet.
3. Never delete or rewrite earlier picks. If a score was wrong, fix the result fields and add a note in `inputs.form_note`.
4. Odds are American. Every pick records where the price came from in `odds_source`. `book` stays null until we know the price on the book the user actually used (Hard Rock Bet).
5. Profit is in units at a flat 1 unit stake. For a win: odds/100 if odds are positive, otherwise 100/abs(odds). A loss is -1. A void is 0. Slips use dollars.
6. Double chance results use the score after 90 minutes only.

## Top level
| field | meaning |
|---|---|
| schema_version | 1 |
| picks | list of single-game picks (totals and double chance) |
| slips | list of multi-leg slips (separate from picks) |

## Pick fields
| field | type | meaning |
|---|---|---|
| id | string | `date-match-market`, unique |
| logged_at | string or null | when the pick was recorded. Null for backfilled history |
| backfilled | bool | true for history loaded from the Excel tracker |
| source | string | `backfill`, `scheduled`, or `manual` |
| date | string | match date, YYYY-MM-DD |
| kickoff_et | string or null | kickoff in Eastern time, for example `3:00 PM` |
| league | string or null | league name (not recorded for Oct 31) |
| match | string | `Home v Away` using DataGaffer names |
| bet_type | string | `single` or `double_chance` |
| market | string | `over_2_5`, `under_3_5`, `home_over_1_5`, or `1X`, `X2`, `12` |
| line_group | string | `main` (2.5 line), `alt` (3.5 line), `watch` (near miss tracked for testing), `shortlist` (double chance) |
| side, line, goals_basis | | over or under, the line, `total` or `home_team` |
| odds_american | int or null | price at logging |
| odds_source | string | where the price came from |
| book | string or null | book the user placed it with, when known |
| model_prob | number | DataGaffer's chance for that market (0 to 1) |
| sofascore_check | string | my pre-kickoff label: Supported, Mostly supported, Mixed, Mixed to against, Not supported, Not checked |
| inputs | object | `projected_total`, `pace`, `regression`, `form_note`. Double chance adds `home_win_pct`, `draw_pct`, `away_win_pct` |
| placed | bool or null | true if the user actually bet it, null if unknown |
| stake_units | number | 1 |
| stake_dollars | number or null | real stake when known |
| home_goals, away_goals, status | | final score and `Final`, `Abandoned` or null while pending |
| result | string or null | `win`, `loss`, `void`, `pending` |
| profit_units | number or null | see rule 5 |
| closing_odds_american | int or null | price at kickoff, to measure whether we beat the closing line |

## Slip fields
`id`, `logged_at`, `backfilled`, `source`, `date`, `name`, `bet_type` (`slip`), `legs` (list of `match`, `call`, `odds_american`, `model_prob`), `n_legs`, `combined_prob_model`, `combined_odds_american`, `odds_source`, `book`, `profit_boost_pct`, `stake_dollars`, `placed`, `note`, `result`, `profit_dollars`, `closing_odds_american`.

All 7 slips loaded so far are drafts built from converted Bet365 prices (`placed: false`). The two real Hard Rock slips from Oct 31 are not included because we do not have all their legs.

## Suggested additions (not in v1 yet)
- `edge_pts` (model chance minus the chance the price implies), computed by the dashboard.
- `my_sim_prob`, so the dashboard can chart both models against results.
- `closing_odds_american` gets filled only when a run can read the closing price.
