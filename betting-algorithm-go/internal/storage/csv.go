package storage

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// MatchRecord represents a single row from the historical dataset CSV.
type MatchRecord struct {
	Date               string  `json:"date"`
	Season             string  `json:"season"`
	HomeTeam           string  `json:"home_team"`
	AwayTeam           string  `json:"away_team"`
	HomeGoals          int     `json:"home_goals"`
	AwayGoals          int     `json:"away_goals"`
	HomeOdds           float64 `json:"home_odds"`
	DrawOdds           float64 `json:"draw_odds"`
	AwayOdds           float64 `json:"away_odds"`
	HomeShots          int     `json:"home_shots"`
	AwayShots          int     `json:"away_shots"`
	HomeShotsOnTarget  int     `json:"home_shots_on_target"`
	AwayShotsOnTarget  int     `json:"away_shots_on_target"`
	MatchID            int     `json:"match_id"`
	HomeXG             float64 `json:"home_xg"`
	AwayXG             float64 `json:"away_xg"`
	HomeElo            float64 `json:"home_elo"`
	AwayElo            float64 `json:"away_elo"`
	HomeForm           string  `json:"home_form"`
	AwayForm           string  `json:"away_form"`
	HomeRestDays       int     `json:"home_rest_days"`
	AwayRestDays       int     `json:"away_rest_days"`
	HomeGamesLast7     int     `json:"home_games_last_7"`
	AwayGamesLast7     int     `json:"away_games_last_7"`
	HomePossession     float64 `json:"home_possession"`
	AwayPossession     float64 `json:"away_possession"`
	HomePPDA           float64 `json:"home_ppda"`
	AwayPPDA           float64 `json:"away_ppda"`
	HomePosition       int     `json:"home_position"`
	AwayPosition       int     `json:"away_position"`
}

// CSVStore handles reading and writing CSV files.
type CSVStore struct {
	DataDir string
}

// NewCSVStore creates a new CSVStore with the given data directory.
func NewCSVStore(dataDir string) *CSVStore {
	return &CSVStore{DataDir: dataDir}
}

// ReadHistoricalData reads the historical dataset CSV file.
func (s *CSVStore) ReadHistoricalData(filePath string) ([]MatchRecord, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("opening CSV file: %w", err)
	}
	defer f.Close()

	reader := csv.NewReader(f)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("reading CSV: %w", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("CSV file has no data rows")
	}

	// Build header index
	header := records[0]
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}

	var matches []MatchRecord
	for i, row := range records[1:] {
		m, err := parseMatchRecord(row, idx)
		if err != nil {
			return nil, fmt.Errorf("parsing row %d: %w", i+2, err)
		}
		matches = append(matches, m)
	}

	return matches, nil
}

// WriteHistoricalData writes match records to a CSV file.
func (s *CSVStore) WriteHistoricalData(filePath string, matches []MatchRecord) error {
	f, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("creating CSV file: %w", err)
	}
	defer f.Close()

	writer := csv.NewWriter(f)
	defer writer.Flush()

	// Write header
	header := []string{
		"Date", "Season", "home_team", "away_team", "home_goals", "away_goals",
		"home_odds", "draw_odds", "away_odds", "home_shots", "away_shots",
		"home_shots_on_target", "away_shots_on_target", "match_id",
		"home_xg", "away_xg", "home_elo", "away_elo", "home_form", "away_form",
		"home_rest_days", "away_rest_days", "home_games_last_7", "away_games_last_7",
		"home_possession", "away_possession", "home_ppda", "away_ppda",
		"home_position", "away_position",
	}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("writing header: %w", err)
	}

	for _, m := range matches {
		row := []string{
			m.Date, m.Season, m.HomeTeam, m.AwayTeam,
			strconv.Itoa(m.HomeGoals), strconv.Itoa(m.AwayGoals),
			fmt.Sprintf("%.2f", m.HomeOdds), fmt.Sprintf("%.2f", m.DrawOdds), fmt.Sprintf("%.2f", m.AwayOdds),
			strconv.Itoa(m.HomeShots), strconv.Itoa(m.AwayShots),
			strconv.Itoa(m.HomeShotsOnTarget), strconv.Itoa(m.AwayShotsOnTarget),
			strconv.Itoa(m.MatchID),
			fmt.Sprintf("%.2f", m.HomeXG), fmt.Sprintf("%.2f", m.AwayXG),
			fmt.Sprintf("%.1f", m.HomeElo), fmt.Sprintf("%.1f", m.AwayElo),
			m.HomeForm, m.AwayForm,
			strconv.Itoa(m.HomeRestDays), strconv.Itoa(m.AwayRestDays),
			strconv.Itoa(m.HomeGamesLast7), strconv.Itoa(m.AwayGamesLast7),
			fmt.Sprintf("%.1f", m.HomePossession), fmt.Sprintf("%.1f", m.AwayPossession),
			fmt.Sprintf("%.6f", m.HomePPDA), fmt.Sprintf("%.6f", m.AwayPPDA),
			strconv.Itoa(m.HomePosition), strconv.Itoa(m.AwayPosition),
		}
		if err := writer.Write(row); err != nil {
			return fmt.Errorf("writing row: %w", err)
		}
	}

	return nil
}

func parseMatchRecord(row []string, idx map[string]int) (MatchRecord, error) {
	m := MatchRecord{
		Date:     getCol(row, idx, "Date"),
		Season:   getCol(row, idx, "Season"),
		HomeTeam: getCol(row, idx, "home_team"),
		AwayTeam: getCol(row, idx, "away_team"),
		HomeForm: getCol(row, idx, "home_form"),
		AwayForm: getCol(row, idx, "away_form"),
	}

	var err error
	m.HomeGoals, err = getColInt(row, idx, "home_goals")
	if err != nil {
		return m, err
	}
	m.AwayGoals, err = getColInt(row, idx, "away_goals")
	if err != nil {
		return m, err
	}
	m.HomeOdds, _ = getColFloat(row, idx, "home_odds")
	m.DrawOdds, _ = getColFloat(row, idx, "draw_odds")
	m.AwayOdds, _ = getColFloat(row, idx, "away_odds")
	m.HomeShots, _ = getColInt(row, idx, "home_shots")
	m.AwayShots, _ = getColInt(row, idx, "away_shots")
	m.HomeShotsOnTarget, _ = getColInt(row, idx, "home_shots_on_target")
	m.AwayShotsOnTarget, _ = getColInt(row, idx, "away_shots_on_target")
	m.MatchID, _ = getColInt(row, idx, "match_id")
	m.HomeXG, _ = getColFloat(row, idx, "home_xg")
	m.AwayXG, _ = getColFloat(row, idx, "away_xg")
	m.HomeElo, _ = getColFloat(row, idx, "home_elo")
	m.AwayElo, _ = getColFloat(row, idx, "away_elo")
	m.HomeRestDays, _ = getColInt(row, idx, "home_rest_days")
	m.AwayRestDays, _ = getColInt(row, idx, "away_rest_days")
	m.HomeGamesLast7, _ = getColInt(row, idx, "home_games_last_7")
	m.AwayGamesLast7, _ = getColInt(row, idx, "away_games_last_7")
	m.HomePossession, _ = getColFloat(row, idx, "home_possession")
	m.AwayPossession, _ = getColFloat(row, idx, "away_possession")
	m.HomePPDA, _ = getColFloat(row, idx, "home_ppda")
	m.AwayPPDA, _ = getColFloat(row, idx, "away_ppda")
	m.HomePosition, _ = getColInt(row, idx, "home_position")
	m.AwayPosition, _ = getColInt(row, idx, "away_position")

	return m, nil
}

func getCol(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func getColInt(row []string, idx map[string]int, col string) (int, error) {
	s := getCol(row, idx, col)
	if s == "" {
		return 0, nil
	}
	// Handle float-formatted ints like "1500.0"
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), nil
	}
	return strconv.Atoi(s)
}

func getColFloat(row []string, idx map[string]int, col string) (float64, error) {
	s := getCol(row, idx, col)
	if s == "" {
		return 0, nil
	}
	return strconv.ParseFloat(s, 64)
}
