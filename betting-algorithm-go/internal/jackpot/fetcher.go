package jackpot

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// JackpotMatch represents a single match within a jackpot.
type JackpotMatch struct {
	MatchNumber int     `json:"match_number"`
	HomeTeam    string  `json:"home_team"`
	AwayTeam    string  `json:"away_team"`
	Kickoff     string  `json:"kickoff"`
	Competition string  `json:"competition"`
	HomeOdds    float64 `json:"home_odds,omitempty"`
	DrawOdds    float64 `json:"draw_odds,omitempty"`
	AwayOdds    float64 `json:"away_odds,omitempty"`
}

// JackpotData holds a fetched jackpot's full details.
type JackpotData struct {
	Provider     string         `json:"provider"`
	Type         string         `json:"type"`
	MatchesCount int            `json:"matches_count"`
	FetchedAt    string         `json:"fetched_at"`
	URL          string         `json:"url"`
	Matches      []JackpotMatch `json:"matches"`
	PrizeAmount  string         `json:"prize_amount,omitempty"`
}

// JackpotHistoryRow is one row in the jackpot_history.csv master file.
type JackpotHistoryRow struct {
	Timestamp    string
	Provider     string
	Type         string
	MatchesCount int
	PrizeAmount  string
	URL          string
}

// JackpotFetcher fetches jackpot matches from Kenyan betting sites.
// Since SportPesa and Betika render their jackpot pages via JavaScript,
// static HTML scraping always falls back to representative sample data.
type JackpotFetcher struct {
	httpClient *http.Client
	historyDir string
	logger     *slog.Logger
}

// NewJackpotFetcher creates a new JackpotFetcher.
//
//   - dataDir  base data directory; jackpot history goes to dataDir/jackpots/
//   - httpClient optional; defaults to 15-second timeout client
//   - logger optional; defaults to slog.Default()
func NewJackpotFetcher(dataDir string, httpClient *http.Client, logger *slog.Logger) *JackpotFetcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 15 * time.Second}
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &JackpotFetcher{
		httpClient: httpClient,
		historyDir: filepath.Join(dataDir, "jackpots"),
		logger:     logger,
	}
}

// FetchSportPesaMegaJackpot fetches the SportPesa Mega Jackpot (17 matches).
// Returns sample data when the live page is not parseable (JS-rendered).
func (f *JackpotFetcher) FetchSportPesaMegaJackpot() (*JackpotData, error) {
	f.logger.Info("Fetching SportPesa Mega Jackpot...")
	const url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"

	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Mega Jackpot",
		MatchesCount: 17,
		FetchedAt:    time.Now().Format(time.RFC3339),
		URL:          url,
	}

	body, err := f.fetchPage(url)
	if err != nil {
		f.logger.Warn("SportPesa Mega Jackpot fetch failed; using sample data", "error", err)
		data.Matches = sampleSportPesaMatches()
	} else {
		data.PrizeAmount = f.extractPrizeAmount(body)
		data.Matches = f.extractMatches(body, "sportpesa")
		if len(data.Matches) == 0 {
			f.logger.Warn("No matches extracted from SportPesa page; using sample data")
			data.Matches = sampleSportPesaMatches()
		}
	}

	data.MatchesCount = len(data.Matches)

	if err := f.saveJackpotHistory(data); err != nil {
		f.logger.Warn("Could not save SportPesa Mega Jackpot history", "error", err)
	}

	f.logger.Info("SportPesa Mega Jackpot fetched",
		"matches", data.MatchesCount,
		"prize", data.PrizeAmount)
	return data, nil
}

// FetchSportPesaMidweekJackpot fetches the SportPesa Midweek Jackpot (13 matches).
// Returns sample data when the live page is not parseable (JS-rendered).
func (f *JackpotFetcher) FetchSportPesaMidweekJackpot() (*JackpotData, error) {
	f.logger.Info("Fetching SportPesa Midweek Jackpot...")
	const url = "https://www.ke.sportpesa.com/en/jackpot"

	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Midweek Jackpot",
		MatchesCount: 13,
		FetchedAt:    time.Now().Format(time.RFC3339),
		URL:          url,
	}

	body, err := f.fetchPage(url)
	if err != nil {
		f.logger.Warn("SportPesa Midweek Jackpot fetch failed; using sample data", "error", err)
		data.Matches = sampleSportPesaMidweekMatches()
	} else {
		data.PrizeAmount = f.extractPrizeAmount(body)
		data.Matches = f.extractMatches(body, "sportpesa")
		if len(data.Matches) == 0 {
			f.logger.Warn("No matches extracted from SportPesa midweek page; using sample data")
			data.Matches = sampleSportPesaMidweekMatches()
		}
	}

	data.MatchesCount = len(data.Matches)

	if err := f.saveJackpotHistory(data); err != nil {
		f.logger.Warn("Could not save SportPesa Midweek Jackpot history", "error", err)
	}

	f.logger.Info("SportPesa Midweek Jackpot fetched",
		"matches", data.MatchesCount,
		"prize", data.PrizeAmount)
	return data, nil
}

// FetchBetikaJackpot fetches the Betika Jackpot.
// Returns sample data when the live page is not parseable (JS-rendered).
func (f *JackpotFetcher) FetchBetikaJackpot() (*JackpotData, error) {
	f.logger.Info("Fetching Betika Jackpot...")
	const url = "https://www.betika.com/en-ke/jackpot"

	data := &JackpotData{
		Provider:  "Betika",
		Type:      "Jackpot",
		FetchedAt: time.Now().Format(time.RFC3339),
		URL:       url,
	}

	body, err := f.fetchPage(url)
	if err != nil {
		f.logger.Warn("Betika Jackpot fetch failed; using sample data", "error", err)
		data.Matches = sampleBetikaMatches()
	} else {
		data.PrizeAmount = f.extractPrizeAmount(body)
		data.Matches = f.extractMatches(body, "betika")
		if len(data.Matches) == 0 {
			f.logger.Warn("No matches extracted from Betika page; using sample data")
			data.Matches = sampleBetikaMatches()
		}
	}

	data.MatchesCount = len(data.Matches)

	if err := f.saveJackpotHistory(data); err != nil {
		f.logger.Warn("Could not save Betika Jackpot history", "error", err)
	}

	f.logger.Info("Betika Jackpot fetched",
		"matches", data.MatchesCount,
		"prize", data.PrizeAmount)
	return data, nil
}

// GetAllCurrentJackpots fetches all three currently supported jackpots in sequence.
// Errors from individual jackpots are logged and skipped rather than propagated.
func (f *JackpotFetcher) GetAllCurrentJackpots() []*JackpotData {
	var result []*JackpotData

	if mega, err := f.FetchSportPesaMegaJackpot(); err == nil {
		result = append(result, mega)
	}
	if midweek, err := f.FetchSportPesaMidweekJackpot(); err == nil {
		result = append(result, midweek)
	}
	if betika, err := f.FetchBetikaJackpot(); err == nil {
		result = append(result, betika)
	}

	return result
}

// GetJackpotHistory reads the master jackpot_history.csv and returns filtered rows.
// Passing empty strings for provider or jackpotType skips that filter.
func (f *JackpotFetcher) GetJackpotHistory(provider, jackpotType string) ([]JackpotHistoryRow, error) {
	csvPath := filepath.Join(f.historyDir, "jackpot_history.csv")
	f1, err := os.Open(csvPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil // no history yet is not an error
		}
		return nil, fmt.Errorf("opening jackpot history: %w", err)
	}
	defer f1.Close()

	r := csv.NewReader(f1)
	records, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("reading jackpot history CSV: %w", err)
	}

	if len(records) < 2 {
		return nil, nil // header only or empty
	}

	// Build column index from header row
	header := records[0]
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[h] = i
	}

	var rows []JackpotHistoryRow
	for _, rec := range records[1:] {
		if len(rec) < len(header) {
			continue
		}
		row := JackpotHistoryRow{
			Timestamp:   safeGet(rec, idx, "timestamp"),
			Provider:    safeGet(rec, idx, "provider"),
			Type:        safeGet(rec, idx, "type"),
			PrizeAmount: safeGet(rec, idx, "prize_amount"),
			URL:         safeGet(rec, idx, "url"),
		}
		// Filter
		if provider != "" && !strings.EqualFold(row.Provider, provider) {
			continue
		}
		if jackpotType != "" && !strings.EqualFold(row.Type, jackpotType) {
			continue
		}
		rows = append(rows, row)
	}

	return rows, nil
}

// ─── private helpers ──────────────────────────────────────────────────────────

// fetchPage performs a GET request with a browser-like User-Agent header.
func (f *JackpotFetcher) fetchPage(url string) ([]byte, error) {
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("building request: %w", err)
	}
	req.Header.Set("User-Agent",
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "+
			"(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

	resp, err := f.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("GET %s: HTTP %d", url, resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading response body: %w", err)
	}
	return body, nil
}

// teamPattern matches HTML elements that commonly contain team names.
var teamPattern = regexp.MustCompile(`(?i)class="[^"]*(?:team|opponent)[^"]*"[^>]*>([^<]{3,40})<`)

// extractMatches attempts to parse team names from raw HTML.
// Because SportPesa and Betika render via JavaScript, this almost always
// returns an empty slice, triggering the sample data fallback in the callers.
func (f *JackpotFetcher) extractMatches(body []byte, _ string) []JackpotMatch {
	text := string(body)

	// Check for iframe (JS-rendered jackpot content)
	if strings.Contains(strings.ToLower(text), "iframe") &&
		strings.Contains(strings.ToLower(text), "jackpot") {
		f.logger.Info("Jackpot content is inside an iframe — static scraping not possible")
		return nil
	}

	// Try regex-based team extraction
	hits := teamPattern.FindAllStringSubmatch(text, 40)
	var matches []JackpotMatch
	for i := 0; i+1 < len(hits); i += 2 {
		home := strings.TrimSpace(hits[i][1])
		away := strings.TrimSpace(hits[i+1][1])
		if len(home) < 3 || len(away) < 3 {
			continue
		}
		matches = append(matches, JackpotMatch{
			MatchNumber: len(matches) + 1,
			HomeTeam:    home,
			AwayTeam:    away,
		})
	}

	return matches
}

// prizePatterns are the regexes tried in order to locate a prize amount in page text.
var prizePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)KSh?\s*[\d,]+`),
	regexp.MustCompile(`(?i)Ksh\s*[\d,]+`),
	regexp.MustCompile(`(?i)[\d,]+\s*Million`),
	regexp.MustCompile(`(?i)Prize:?\s*[\d,]+`),
}

// extractPrizeAmount scans raw HTML text for a prize amount string.
func (f *JackpotFetcher) extractPrizeAmount(body []byte) string {
	text := string(body)
	for _, re := range prizePatterns {
		if m := re.FindString(text); m != "" {
			return m
		}
	}
	return ""
}

// saveJackpotHistory writes jackpot data as a timestamped JSON file and
// appends a summary row to the master jackpot_history.csv.
func (f *JackpotFetcher) saveJackpotHistory(data *JackpotData) error {
	if err := os.MkdirAll(f.historyDir, 0o755); err != nil {
		return fmt.Errorf("creating history dir: %w", err)
	}

	ts := time.Now().Format("20060102_150405")
	provider := strings.ToLower(strings.ReplaceAll(data.Provider, " ", "_"))
	jpType := strings.ToLower(strings.ReplaceAll(data.Type, " ", "_"))
	filename := fmt.Sprintf("%s_%s_%s.json", provider, jpType, ts)
	filepath_ := filepath.Join(f.historyDir, filename)

	raw, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("marshaling jackpot JSON: %w", err)
	}
	if err := os.WriteFile(filepath_, raw, 0o644); err != nil {
		return fmt.Errorf("writing jackpot JSON: %w", err)
	}
	f.logger.Info("Saved jackpot history", "file", filepath_)

	return f.appendToMasterCSV(data)
}

// appendToMasterCSV appends one summary row to jackpot_history.csv.
func (f *JackpotFetcher) appendToMasterCSV(data *JackpotData) error {
	csvPath := filepath.Join(f.historyDir, "jackpot_history.csv")

	// Determine if header is needed
	needsHeader := true
	if _, err := os.Stat(csvPath); err == nil {
		needsHeader = false
	}

	f1, err := os.OpenFile(csvPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return fmt.Errorf("opening jackpot_history.csv: %w", err)
	}
	defer f1.Close()

	w := csv.NewWriter(f1)
	if needsHeader {
		if err := w.Write([]string{"timestamp", "provider", "type", "matches_count", "prize_amount", "url"}); err != nil {
			return err
		}
	}
	if err := w.Write([]string{
		data.FetchedAt,
		data.Provider,
		data.Type,
		fmt.Sprintf("%d", data.MatchesCount),
		data.PrizeAmount,
		data.URL,
	}); err != nil {
		return err
	}
	w.Flush()
	return w.Error()
}

// safeGet retrieves a CSV column value by name, returning "" if not found.
func safeGet(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return row[i]
}

// ─── sample data ─────────────────────────────────────────────────────────────

// sampleSportPesaMatches returns the 17-match SportPesa Mega Jackpot sample.
func sampleSportPesaMatches() []JackpotMatch {
	return []JackpotMatch{
		{1, "Arsenal", "Chelsea", "Sat 15:00", "Premier League", 0, 0, 0},
		{2, "Man City", "Liverpool", "Sat 17:30", "Premier League", 0, 0, 0},
		{3, "Tottenham", "Man United", "Sat 15:00", "Premier League", 0, 0, 0},
		{4, "Real Madrid", "Barcelona", "Sat 20:00", "La Liga", 0, 0, 0},
		{5, "Bayern Munich", "Dortmund", "Sat 17:30", "Bundesliga", 0, 0, 0},
		{6, "Inter Milan", "AC Milan", "Sat 19:45", "Serie A", 0, 0, 0},
		{7, "PSG", "Marseille", "Sat 20:00", "Ligue 1", 0, 0, 0},
		{8, "Juventus", "Napoli", "Sat 17:00", "Serie A", 0, 0, 0},
		{9, "Atletico Madrid", "Sevilla", "Sat 18:30", "La Liga", 0, 0, 0},
		{10, "Leicester", "West Ham", "Sat 15:00", "Premier League", 0, 0, 0},
		{11, "Newcastle", "Aston Villa", "Sat 15:00", "Premier League", 0, 0, 0},
		{12, "Brighton", "Wolves", "Sat 15:00", "Premier League", 0, 0, 0},
		{13, "Everton", "Southampton", "Sat 15:00", "Premier League", 0, 0, 0},
		{14, "Leeds United", "Burnley", "Sat 15:00", "Championship", 0, 0, 0},
		{15, "Sheffield United", "Norwich", "Sat 15:00", "Championship", 0, 0, 0},
		{16, "Brentford", "Fulham", "Sat 15:00", "Premier League", 0, 0, 0},
		{17, "Crystal Palace", "Bournemouth", "Sat 15:00", "Premier League", 0, 0, 0},
	}
}

// sampleSportPesaMidweekMatches returns the 13-match SportPesa Midweek Jackpot sample.
func sampleSportPesaMidweekMatches() []JackpotMatch {
	return []JackpotMatch{
		{1, "Arsenal", "Brighton", "Wed 19:45", "Premier League", 0, 0, 0},
		{2, "Chelsea", "Newcastle", "Wed 19:45", "Premier League", 0, 0, 0},
		{3, "Man City", "Aston Villa", "Wed 20:00", "Premier League", 0, 0, 0},
		{4, "Liverpool", "Wolves", "Wed 19:45", "Premier League", 0, 0, 0},
		{5, "Tottenham", "Everton", "Wed 19:45", "Premier League", 0, 0, 0},
		{6, "Real Madrid", "Atletico Madrid", "Wed 21:00", "La Liga", 0, 0, 0},
		{7, "Barcelona", "Sevilla", "Wed 21:00", "La Liga", 0, 0, 0},
		{8, "Bayern Munich", "Leverkusen", "Wed 20:30", "Bundesliga", 0, 0, 0},
		{9, "Dortmund", "RB Leipzig", "Wed 20:30", "Bundesliga", 0, 0, 0},
		{10, "Inter Milan", "Napoli", "Wed 20:45", "Serie A", 0, 0, 0},
		{11, "Juventus", "Roma", "Wed 20:45", "Serie A", 0, 0, 0},
		{12, "PSG", "Lyon", "Wed 21:00", "Ligue 1", 0, 0, 0},
		{13, "Ajax", "PSV", "Wed 20:00", "Eredivisie", 0, 0, 0},
	}
}

// sampleBetikaMatches returns the 15-match Betika Jackpot sample.
func sampleBetikaMatches() []JackpotMatch {
	return []JackpotMatch{
		{1, "Arsenal", "Liverpool", "Sat 15:00", "Premier League", 0, 0, 0},
		{2, "Man City", "Chelsea", "Sat 17:30", "Premier League", 0, 0, 0},
		{3, "Real Madrid", "Atletico Madrid", "Sat 20:00", "La Liga", 0, 0, 0},
		{4, "Barcelona", "Sevilla", "Sat 18:30", "La Liga", 0, 0, 0},
		{5, "Bayern Munich", "RB Leipzig", "Sat 17:30", "Bundesliga", 0, 0, 0},
		{6, "Inter Milan", "Juventus", "Sat 19:45", "Serie A", 0, 0, 0},
		{7, "PSG", "Lyon", "Sat 20:00", "Ligue 1", 0, 0, 0},
		{8, "Tottenham", "Newcastle", "Sat 15:00", "Premier League", 0, 0, 0},
		{9, "Man United", "West Ham", "Sat 17:00", "Premier League", 0, 0, 0},
		{10, "Napoli", "Roma", "Sat 17:00", "Serie A", 0, 0, 0},
		{11, "Dortmund", "Leverkusen", "Sat 15:30", "Bundesliga", 0, 0, 0},
		{12, "Ajax", "PSV", "Sat 19:45", "Eredivisie", 0, 0, 0},
		{13, "Benfica", "Porto", "Sat 20:30", "Primeira Liga", 0, 0, 0},
		{14, "Celtic", "Rangers", "Sat 15:00", "Scottish Premiership", 0, 0, 0},
		{15, "Sporting CP", "Braga", "Sat 18:00", "Primeira Liga", 0, 0, 0},
	}
}
