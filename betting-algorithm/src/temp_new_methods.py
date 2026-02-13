
    # ========================================================================
    # NEW CONTEXTUAL FACTORS (Version 2.0 - Enhanced Draw Prediction)
    # ========================================================================

    def _calculate_h2h_factors(self, match_data: Dict, context) -> tuple:
        """
        Calculate H2H historical and anomaly factors.

        Returns tuple: (historical_factor, anomaly_factor)
        - Only one is active at a time (anomaly replaces historical when triggered)
        """
        from .models import FactorResult

        if context.h2hRecord is None:
            # No H2H data available - return inactive factors
            return (
                FactorResult(
                    name='h2hHistorical',
                    value=0.5,
                    weight=0.0,  # inactive
                    triggered=False,
                    confidence=0,
                    explanation="No H2H data available"
                ),
                FactorResult(
                    name='h2hAnomaly',
                    value=0.5,
                    weight=0.0,
                    triggered=False,
                    confidence=0,
                    explanation="No H2H data for anomaly detection"
                )
            )

        h2h = context.h2hRecord

        # Calculate base H2H score from win/draw/loss ratio
        if h2h.total_matches == 0:
            h2h_score = 0.5
            confidence = 0
        else:
            home_win_rate = h2h.home_wins / h2h.total_matches
            # Normalize: 33% = neutral (0.5), 66% = strong home (0.75), 0% = strong away (0.25)
            h2h_score = 0.5 + (home_win_rate - 0.33) * 0.5
            confidence = min(h2h.total_matches * 10, 100)

        # Check for H2H anomaly
        weaker_team_is_home = context.homeLeaguePosition > context.awayLeaguePosition
        anomaly_detected = h2h.anomalyTriggered and h2h.weakerTeamUnbeatenStreak >= 3

        if anomaly_detected:
            # H2H anomaly takes over - weaker team has persistent good record
            anomaly_boost = 0.2 if weaker_team_is_home else -0.1

            return (
                FactorResult(
                    name='h2hHistorical',
                    value=h2h_score,
                    weight=0.0,  # replaced by anomaly
                    triggered=False,
                    confidence=confidence,
                    explanation=f"H2H replaced by anomaly (streak: {h2h.weakerTeamUnbeatenStreak})"
                ),
                FactorResult(
                    name='h2hAnomaly',
                    value=0.5 + anomaly_boost,
                    weight=0.15,  # boosted weight (3x base)
                    triggered=True,
                    confidence=90,
                    explanation=f"Weaker team unbeaten in {h2h.weakerTeamUnbeatenStreak} consecutive H2H",
                    metadata={
                        'streak': h2h.weakerTeamUnbeatenStreak,
                        'weaker_team_home': weaker_team_is_home,
                        'h2h_record': f"{h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L"
                    }
                )
            )
        else:
            # Normal H2H factor (no anomaly)
            return (
                FactorResult(
                    name='h2hHistorical',
                    value=h2h_score,
                    weight=0.05,
                    triggered=True,
                    confidence=confidence,
                    explanation=f"H2H record: {h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L (last {h2h.total_matches})"
                ),
                FactorResult(
                    name='h2hAnomaly',
                    value=0.5,
                    weight=0.0,
                    triggered=False,
                    confidence=50,
                    explanation="No anomaly detected (streak < 3)"
                )
            )
