package storage

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// MatchRecord represents a single row from a historical CSV dataset.
type MatchRecord struct {
	Date       string  `json:"date"`
	HomeTeam   string  `json:"home_team"`
	AwayTeam   string  `json:"away_team"`
	HomeGoals  int     `json:"home_goals"`
	AwayGoals  int     `json:"away_goals"`
	HomeOdds   float64 `json:"home_odds"`
	DrawOdds   float64 `json:"draw_odds"`
	AwayOdds   float64 `json:"away_odds"`
	HomeXG     float64 `json:"home_xg"`
	AwayXG     float64 `json:"away_xg"`
	HomeElo    float64 `json:"home_elo"`
	AwayElo    float64 `json:"away_elo"`
	HomeForm   string  `json:"home_form"`
	AwayForm   string  `json:"away_form"`
	HomePos    int     `json:"home_position"`
	AwayPos    int     `json:"away_position"`
	Season     string  `json:"season"`
	League     string  `json:"league"`
	RestDaysH  int     `json:"rest_days_home"`
	RestDaysA  int     `json:"rest_days_away"`
	Result     string  `json:"result"` // "H", "D", "A"
}

// CSVStore handles reading and writing CSV data.
type CSVStore struct {
	DataDir string
}

// NewCSVStore creates a new CSV store rooted at the given data directory.
func NewCSVStore(dataDir string) *CSVStore {
	return &CSVStore{DataDir: dataDir}
}

// ReadHistoricalData reads the historical dataset CSV.
func (s *CSVStore) ReadHistoricalData(filename string) ([]MatchRecord, error) {
	path := s.DataDir + "/" + filename
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	return parseMatchCSV(f)
}

// WriteHistoricalData writes match records to a CSV file.
func (s *CSVStore) WriteHistoricalData(filename string, records []MatchRecord) error {
	path := s.DataDir + "/" + filename

	// Ensure directory exists
	dir := path[:strings.LastIndex(path, "/")]
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}

	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	defer w.Flush()

	// Write header
	header := []string{
		"Date", "HomeTeam", "AwayTeam", "HomeGoals", "AwayGoals",
		"HomeOdds", "DrawOdds", "AwayOdds", "HomeXG", "AwayXG",
		"HomeElo", "AwayElo", "HomeForm", "AwayForm",
		"HomePosition", "AwayPosition", "Season", "League",
		"RestDaysHome", "RestDaysAway", "Result",
	}
	if err := w.Write(header); err != nil {
		return fmt.Errorf("write header: %w", err)
	}

	for _, r := range records {
		row := []string{
			r.Date, r.HomeTeam, r.AwayTeam,
			strconv.Itoa(r.HomeGoals), strconv.Itoa(r.AwayGoals),
			formatFloat(r.HomeOdds), formatFloat(r.DrawOdds), formatFloat(r.AwayOdds),
			formatFloat(r.HomeXG), formatFloat(r.AwayXG),
			formatFloat(r.HomeElo), formatFloat(r.AwayElo),
			r.HomeForm, r.AwayForm,
			strconv.Itoa(r.HomePos), strconv.Itoa(r.AwayPos),
			r.Season, r.League,
			strconv.Itoa(r.RestDaysH), strconv.Itoa(r.RestDaysA),
			r.Result,
		}
		if err := w.Write(row); err != nil {
			return fmt.Errorf("write row: %w", err)
		}
	}

	return nil
}

// Exists checks if a data file exists.
func (s *CSVStore) Exists(filename string) bool {
	path := s.DataDir + "/" + filename
	_, err := os.Stat(path)
	return err == nil
}

func parseMatchCSV(r io.Reader) ([]MatchRecord, error) {
	reader := csv.NewReader(r)
	reader.LazyQuotes = true
	reader.TrimLeadingSpace = true

	// Read header
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	// Build column index map
	colIdx := make(map[string]int)
	for i, name := range header {
		colIdx[strings.TrimSpace(name)] = i
	}

	var records []MatchRecord
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}

		rec := MatchRecord{
			Date:      getCol(row, colIdx, "Date"),
			HomeTeam:  getCol(row, colIdx, "HomeTeam", "home_team"),
			AwayTeam:  getCol(row, colIdx, "AwayTeam", "away_team"),
			HomeGoals: getColInt(row, colIdx, "HomeGoals", "home_goals", "FTHG"),
			AwayGoals: getColInt(row, colIdx, "AwayGoals", "away_goals", "FTAG"),
			HomeOdds:  getColFloat(row, colIdx, "HomeOdds", "home_odds", "B365H", "PSH"),
			DrawOdds:  getColFloat(row, colIdx, "DrawOdds", "draw_odds", "B365D", "PSD"),
			AwayOdds:  getColFloat(row, colIdx, "AwayOdds", "away_odds", "B365A", "PSA"),
			HomeXG:    getColFloat(row, colIdx, "HomeXG", "home_xg"),
			AwayXG:    getColFloat(row, colIdx, "AwayXG", "away_xg"),
			HomeElo:   getColFloat(row, colIdx, "HomeElo", "home_elo"),
			AwayElo:   getColFloat(row, colIdx, "AwayElo", "away_elo"),
			HomeForm:  getCol(row, colIdx, "HomeForm", "home_form"),
			AwayForm:  getCol(row, colIdx, "AwayForm", "away_form"),
			HomePos:   getColInt(row, colIdx, "HomePosition", "home_position"),
			AwayPos:   getColInt(row, colIdx, "AwayPosition", "away_position"),
			Season:    getCol(row, colIdx, "Season", "season"),
			League:    getCol(row, colIdx, "League", "league", "Div"),
			RestDaysH: getColInt(row, colIdx, "RestDaysHome", "rest_days_home"),
			RestDaysA: getColInt(row, colIdx, "RestDaysAway", "rest_days_away"),
			Result:    getCol(row, colIdx, "Result", "result", "FTR"),
		}
		records = append(records, rec)
	}

	return records, nil
}

// getCol returns the first matching column value from a row.
func getCol(row []string, idx map[string]int, names ...string) string {
	for _, name := range names {
		if i, ok := idx[name]; ok && i < len(row) {
			return strings.TrimSpace(row[i])
		}
	}
	return ""
}

// getColInt returns the first matching column as int.
func getColInt(row []string, idx map[string]int, names ...string) int {
	s := getCol(row, idx, names...)
	if s == "" {
		return 0
	}
	v, _ := strconv.Atoi(s)
	return v
}

// getColFloat returns the first matching column as float64.
func getColFloat(row []string, idx map[string]int, names ...string) float64 {
	s := getCol(row, idx, names...)
	if s == "" {
		return 0
	}
	v, _ := strconv.ParseFloat(s, 64)
	return v
}

func formatFloat(f float64) string {
	return strconv.FormatFloat(f, 'f', -1, 64)
}
