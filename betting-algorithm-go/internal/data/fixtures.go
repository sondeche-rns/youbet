package data

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

// FixtureMatch represents an upcoming or completed match with odds.
type FixtureMatch struct {
	ID           string  `json:"id"`
	Sport        string  `json:"sport"`
	CommenceTime string  `json:"commence_time"`
	HomeTeam     string  `json:"home_team"`
	AwayTeam     string  `json:"away_team"`
	HomeOdds     float64 `json:"home_odds"`
	DrawOdds     float64 `json:"draw_odds"`
	AwayOdds     float64 `json:"away_odds"`
	Bookmakers   int     `json:"bookmakers"`
	Source       string  `json:"source"`
	League       string  `json:"league,omitempty"`
	Season       string  `json:"season,omitempty"`
	HomeGoals    *int    `json:"home_goals,omitempty"`
	AwayGoals    *int    `json:"away_goals,omitempty"`
}

// LiveFixturesFetcher fetches upcoming fixtures and odds.
type LiveFixturesFetcher struct {
	oddsAPIKey     string
	apiFootballKey string
	httpClient     *http.Client
	logger         *slog.Logger
}

// NewLiveFixturesFetcher creates a new fetcher.
func NewLiveFixturesFetcher(oddsAPIKey, apiFootballKey string, httpClient *http.Client, logger *slog.Logger) *LiveFixturesFetcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 10 * time.Second}
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &LiveFixturesFetcher{
		oddsAPIKey:     oddsAPIKey,
		apiFootballKey: apiFootballKey,
		httpClient:     httpClient,
		logger:         logger,
	}
}

// GetUpcomingMatches fetches upcoming matches for the next daysAhead days.
func (f *LiveFixturesFetcher) GetUpcomingMatches(sport string, daysAhead int) ([]FixtureMatch, error) {
	if sport == "" {
		sport = "soccer_epl"
	}
	if daysAhead <= 0 {
		daysAhead = 7
	}

	var matches []FixtureMatch

	// Try The Odds API first
	if f.oddsAPIKey != "" {
		f.logger.Info("Fetching from Odds API", "sport", sport)
		oddsMatches, err := f.fetchFromOddsAPI(sport)
		if err != nil {
			f.logger.Warn("Error fetching from Odds API", "error", err)
		} else {
			f.logger.Info(fmt.Sprintf("Fetched %d matches from Odds API", len(oddsMatches)))
			matches = append(matches, oddsMatches...)
		}
	}

	// If no matches from Odds API, we have no upcoming fixtures
	if len(matches) == 0 {
		f.logger.Info("No upcoming matches from Odds API")
		return nil, nil
	}

	// Filter to upcoming only
	now := time.Now().UTC()
	var upcoming []FixtureMatch
	for _, match := range matches {
		matchTime := parseMatchTime(match.CommenceTime)
		if matchTime.IsZero() {
			continue
		}
		if matchTime.After(now) {
			daysDiff := int(matchTime.Sub(now).Hours() / 24)
			if daysDiff <= daysAhead {
				upcoming = append(upcoming, match)
			}
		}
	}

	f.logger.Info(fmt.Sprintf("Returning %d upcoming matches", len(upcoming)))
	return upcoming, nil
}

// oddsAPIEvent represents an event from The Odds API response.
type oddsAPIEvent struct {
	ID           string          `json:"id"`
	SportKey     string          `json:"sport_key"`
	CommenceTime string          `json:"commence_time"`
	HomeTeam     string          `json:"home_team"`
	AwayTeam     string          `json:"away_team"`
	Bookmakers   []oddsBookmaker `json:"bookmakers"`
}

type oddsBookmaker struct {
	Key     string       `json:"key"`
	Title   string       `json:"title"`
	Markets []oddsMarket `json:"markets"`
}

type oddsMarket struct {
	Key      string        `json:"key"`
	Outcomes []oddsOutcome `json:"outcomes"`
}

type oddsOutcome struct {
	Name  string  `json:"name"`
	Price float64 `json:"price"`
}

// fetchFromOddsAPI fetches from The Odds API.
func (f *LiveFixturesFetcher) fetchFromOddsAPI(sport string) ([]FixtureMatch, error) {
	if f.oddsAPIKey == "" {
		return nil, nil
	}

	url := fmt.Sprintf(
		"https://api.the-odds-api.com/v4/sports/%s/odds?apiKey=%s&regions=uk,eu&markets=h2h&oddsFormat=decimal",
		sport, f.oddsAPIKey,
	)

	resp, err := f.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("fetching odds: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Odds API returned HTTP %d", resp.StatusCode)
	}

	var events []oddsAPIEvent
	if err := json.NewDecoder(resp.Body).Decode(&events); err != nil {
		return nil, fmt.Errorf("decoding odds response: %w", err)
	}

	var matches []FixtureMatch
	for _, event := range events {
		homeOdds, drawOdds, awayOdds := extractBestOdds(event)
		matches = append(matches, FixtureMatch{
			ID:           event.ID,
			Sport:        sport,
			CommenceTime: event.CommenceTime,
			HomeTeam:     event.HomeTeam,
			AwayTeam:     event.AwayTeam,
			HomeOdds:     homeOdds,
			DrawOdds:     drawOdds,
			AwayOdds:     awayOdds,
			Bookmakers:   len(event.Bookmakers),
			Source:       "the-odds-api",
		})
	}

	return matches, nil
}

// extractBestOdds finds the best (highest) odds across bookmakers.
func extractBestOdds(event oddsAPIEvent) (home, draw, away float64) {
	for _, bm := range event.Bookmakers {
		for _, market := range bm.Markets {
			if market.Key != "h2h" {
				continue
			}
			for _, outcome := range market.Outcomes {
				switch outcome.Name {
				case event.HomeTeam:
					if outcome.Price > home {
						home = outcome.Price
					}
				case event.AwayTeam:
					if outcome.Price > away {
						away = outcome.Price
					}
				case "Draw":
					if outcome.Price > draw {
						draw = outcome.Price
					}
				}
			}
		}
	}
	return
}

// GetAvailableSports returns available sports from The Odds API.
func (f *LiveFixturesFetcher) GetAvailableSports() ([]map[string]any, error) {
	if f.oddsAPIKey == "" {
		return nil, nil
	}

	url := fmt.Sprintf("https://api.the-odds-api.com/v4/sports?apiKey=%s", f.oddsAPIKey)
	resp, err := f.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("fetching sports: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("sports API returned HTTP %d", resp.StatusCode)
	}

	var sports []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&sports); err != nil {
		return nil, fmt.Errorf("decoding sports response: %w", err)
	}

	return sports, nil
}

// GetLiveOddsForMatch finds odds for a specific match.
func (f *LiveFixturesFetcher) GetLiveOddsForMatch(homeTeam, awayTeam, sport string) (*FixtureMatch, error) {
	if sport == "" {
		sport = "soccer_epl"
	}

	matches, err := f.GetUpcomingMatches(sport, 30)
	if err != nil {
		return nil, err
	}

	for _, match := range matches {
		if normalizeTeamName(match.HomeTeam) == normalizeTeamName(homeTeam) &&
			normalizeTeamName(match.AwayTeam) == normalizeTeamName(awayTeam) {
			return &match, nil
		}
	}

	return nil, nil
}

// GetQuotaUsage checks API quota usage for The Odds API.
func (f *LiveFixturesFetcher) GetQuotaUsage() (map[string]string, error) {
	if f.oddsAPIKey == "" {
		return nil, nil
	}

	url := fmt.Sprintf("https://api.the-odds-api.com/v4/sports?apiKey=%s", f.oddsAPIKey)
	resp, err := f.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("checking quota: %w", err)
	}
	defer resp.Body.Close()

	return map[string]string{
		"requests_remaining": resp.Header.Get("x-requests-remaining"),
		"requests_used":      resp.Header.Get("x-requests-used"),
		"requests_limit":     resp.Header.Get("x-requests-limit"),
	}, nil
}

// GetCurrentSeasonResults fetches completed matches from the current season.
func (f *LiveFixturesFetcher) GetCurrentSeasonResults(league string) ([]FixtureMatch, error) {
	if league == "" {
		league = "E0"
	}

	// Determine current season code
	now := time.Now()
	var seasonCode string
	if now.Month() >= 8 {
		seasonCode = fmt.Sprintf("%02d%02d", now.Year()%100, (now.Year()+1)%100)
	} else {
		seasonCode = fmt.Sprintf("%02d%02d", (now.Year()-1)%100, now.Year()%100)
	}

	return f.fetchFromFootballDataUK(seasonCode, league)
}

// fetchFromFootballDataUK fetches current season data from football-data.co.uk.
func (f *LiveFixturesFetcher) fetchFromFootballDataUK(seasonCode, league string) ([]FixtureMatch, error) {
	url := fmt.Sprintf("https://www.football-data.co.uk/mmz4281/%s/%s.csv", seasonCode, league)

	resp, err := f.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("fetching %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d for %s", resp.StatusCode, url)
	}

	return parseFootballDataCSV(resp.Body, league, seasonCode)
}

// parseFootballDataCSV parses CSV data from football-data.co.uk into FixtureMatch records.
func parseFootballDataCSV(body io.Reader, league, seasonCode string) ([]FixtureMatch, error) {
	reader := csv.NewReader(body)
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1

	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("parsing CSV: %w", err)
	}

	if len(records) < 2 {
		return nil, nil
	}

	header := records[0]
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}

	var matches []FixtureMatch
	for _, row := range records[1:] {
		date := getCSVCol(row, idx, "Date")
		homeTeam := getCSVCol(row, idx, "HomeTeam")
		awayTeam := getCSVCol(row, idx, "AwayTeam")

		if date == "" || homeTeam == "" {
			continue
		}

		homeGoals := csvColIntPtr(row, idx, "FTHG")
		awayGoals := csvColIntPtr(row, idx, "FTAG")

		homeOdds := getCSVColFloat(row, idx, "B365H", 0)
		if homeOdds == 0 {
			homeOdds = getCSVColFloat(row, idx, "BWH", 0)
		}
		drawOdds := getCSVColFloat(row, idx, "B365D", 0)
		if drawOdds == 0 {
			drawOdds = getCSVColFloat(row, idx, "BWD", 0)
		}
		awayOdds := getCSVColFloat(row, idx, "B365A", 0)
		if awayOdds == 0 {
			awayOdds = getCSVColFloat(row, idx, "BWA", 0)
		}

		matches = append(matches, FixtureMatch{
			CommenceTime: date,
			HomeTeam:     homeTeam,
			AwayTeam:     awayTeam,
			HomeGoals:    homeGoals,
			AwayGoals:    awayGoals,
			HomeOdds:     homeOdds,
			DrawOdds:     drawOdds,
			AwayOdds:     awayOdds,
			League:       league,
			Season:       seasonCode,
			Source:       "football-data-uk",
		})
	}

	return matches, nil
}

// --- Helpers ---

func normalizeTeamName(name string) string {
	return strings.ToLower(strings.ReplaceAll(strings.TrimSpace(name), " ", ""))
}

func parseMatchTime(s string) time.Time {
	if s == "" {
		return time.Time{}
	}

	// ISO format from Odds API (e.g., "2024-02-11T15:00:00Z")
	if strings.Contains(s, "T") || strings.Contains(s, "Z") || strings.Contains(s, "+") {
		if t, err := time.Parse(time.RFC3339, s); err == nil {
			return t
		}
		if t, err := time.Parse("2006-01-02T15:04:05Z", s); err == nil {
			return t.UTC()
		}
	}

	// DD/MM/YYYY from football-data.co.uk
	if t, err := time.Parse("02/01/2006", s); err == nil {
		return t.UTC()
	}
	// DD/MM/YY
	if t, err := time.Parse("02/01/06", s); err == nil {
		return t.UTC()
	}

	return time.Time{}
}

// csvColIntPtr parses a CSV column value as an int pointer (nil if empty).
func csvColIntPtr(row []string, idx map[string]int, col string) *int {
	s := getCSVCol(row, idx, col)
	if s == "" {
		return nil
	}
	var v float64
	if _, err := fmt.Sscanf(s, "%f", &v); err != nil {
		return nil
	}
	intVal := int(v)
	return &intVal
}
