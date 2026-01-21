# Algorithm Weights Documentation

Complete documentation of all prediction factors and their weights.

## Football Configuration

| Factor | Weight | Description |
|--------|--------|-------------|
| Expected Goals (xG) | 20% | xG differential and shot quality |
| Advanced Statistics | 15% | PPDA, progressive passes, shot quality |
| Team Strength (Elo) | 12% | Dynamic Elo rating system |
| Tactical Matchup | 12% | Style vs style analysis |
| Current Form | 10% | Last 10 games weighted by recency |
| Player Impact | 10% | Quantified key player availability |
| Rest & Fatigue | 8% | Rest days, travel, fixture congestion |
| Motivation | 6% | League position, stakes, rivalry |
| Home Advantage | 5% | Venue strength and crowd factor |
| External Factors | 2% | Weather, referee, timezone |

For complete documentation, see the WEIGHTS_DOCUMENTATION artifact.
