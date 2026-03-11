package data

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// DataSourcesConfig holds the top-level data_sources.json structure.
type DataSourcesConfig struct {
	Sources       []DataSource  `json:"sources"`
	DefaultConfig DefaultConfig `json:"default_config"`
}

// DefaultConfig holds the default configuration from data_sources.json.
type DefaultConfig struct {
	Seasons []string `json:"seasons"`
	Leagues []string `json:"leagues"`
}

// DataSource represents a single data source entry.
type DataSource struct {
	ID               string   `json:"id"`
	Name             string   `json:"name"`
	Enabled          bool     `json:"enabled"`
	Type             string   `json:"type"`
	Description      string   `json:"description"`
	BaseURL          string   `json:"base_url"`
	URLPattern       string   `json:"url_pattern"`
	RateLimitSeconds float64  `json:"rate_limit_seconds"`
	TimeoutSeconds   int      `json:"timeout_seconds"`
	Sports           []string `json:"sports"`
	RequiresAPIKey   bool     `json:"requires_api_key"`
	Leagues          []League `json:"leagues"`
	Seasons          []Season `json:"seasons"`
	ColumnMapping    map[string]string `json:"column_mapping"`
}

// League represents a league within a data source.
type League struct {
	Code    string `json:"code"`
	Name    string `json:"name"`
	Country string `json:"country"`
	Tier    int    `json:"tier"`
}

// Season represents a season entry.
type Season struct {
	Code  string `json:"code"`
	Label string `json:"label"`
	Years string `json:"years"`
}

// DataSourcesManager manages data source configurations.
type DataSourcesManager struct {
	configPath string
	Config     *DataSourcesConfig
}

// NewDataSourcesManager creates a new DataSourcesManager and loads the config.
// If the config file cannot be loaded an empty (but non-nil) manager is returned
// so callers can safely call all methods without panicking.
func NewDataSourcesManager(configPath string) (*DataSourcesManager, error) {
	m := &DataSourcesManager{configPath: configPath}
	if err := m.loadConfig(); err != nil {
		return m, err // return the empty manager so callers don't receive nil
	}
	return m, nil
}

func (m *DataSourcesManager) loadConfig() error {
	data, err := os.ReadFile(m.configPath)
	if err != nil {
		return fmt.Errorf("reading config %s: %w", m.configPath, err)
	}
	var cfg DataSourcesConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return fmt.Errorf("parsing config %s: %w", m.configPath, err)
	}
	m.Config = &cfg
	return nil
}

// GetEnabledSources returns all enabled data sources.
func (m *DataSourcesManager) GetEnabledSources() []DataSource {
	if m.Config == nil {
		return nil
	}
	var enabled []DataSource
	for _, s := range m.Config.Sources {
		if s.Enabled {
			enabled = append(enabled, s)
		}
	}
	return enabled
}

// GetSourceByID returns a data source by its ID, or nil if not found.
func (m *DataSourcesManager) GetSourceByID(sourceID string) *DataSource {
	if m.Config == nil {
		return nil
	}
	for i := range m.Config.Sources {
		if m.Config.Sources[i].ID == sourceID {
			return &m.Config.Sources[i]
		}
	}
	return nil
}

// GetAvailableLeagues returns leagues for the given source.
func (m *DataSourcesManager) GetAvailableLeagues(sourceID string) []League {
	src := m.GetSourceByID(sourceID)
	if src == nil {
		return nil
	}
	return src.Leagues
}

// GetAvailableSeasons returns seasons for the given source.
func (m *DataSourcesManager) GetAvailableSeasons(sourceID string) []Season {
	src := m.GetSourceByID(sourceID)
	if src == nil {
		return nil
	}
	return src.Seasons
}

// GetDefaultConfig returns the default configuration.
func (m *DataSourcesManager) GetDefaultConfig() DefaultConfig {
	if m.Config == nil {
		return DefaultConfig{}
	}
	return m.Config.DefaultConfig
}

// GetURLPattern returns the URL pattern for a source.
func (m *DataSourcesManager) GetURLPattern(sourceID string) string {
	src := m.GetSourceByID(sourceID)
	if src == nil {
		return ""
	}
	return src.URLPattern
}

// GetColumnMapping returns the column mapping for a source.
func (m *DataSourcesManager) GetColumnMapping(sourceID string) map[string]string {
	src := m.GetSourceByID(sourceID)
	if src == nil {
		return nil
	}
	return src.ColumnMapping
}

// GetLeaguesByCountry returns leagues filtered by country.
func (m *DataSourcesManager) GetLeaguesByCountry(country, sourceID string) []League {
	leagues := m.GetAvailableLeagues(sourceID)
	var filtered []League
	for _, l := range leagues {
		if strings.EqualFold(l.Country, country) {
			filtered = append(filtered, l)
		}
	}
	return filtered
}

// GetTopTierLeagues returns only tier-1 leagues.
func (m *DataSourcesManager) GetTopTierLeagues(sourceID string) []League {
	leagues := m.GetAvailableLeagues(sourceID)
	var top []League
	for _, l := range leagues {
		if l.Tier == 1 {
			top = append(top, l)
		}
	}
	return top
}

// GetRecentSeasons returns the most recent n seasons.
func (m *DataSourcesManager) GetRecentSeasons(sourceID string, count int) []Season {
	seasons := m.GetAvailableSeasons(sourceID)
	if count > len(seasons) {
		count = len(seasons)
	}
	return seasons[:count]
}

// FormatURL formats a URL for data fetching.
func (m *DataSourcesManager) FormatURL(sourceID, season, league string) string {
	src := m.GetSourceByID(sourceID)
	if src == nil || src.URLPattern == "" || src.BaseURL == "" {
		return ""
	}
	url := strings.ReplaceAll(src.URLPattern, "{base_url}", src.BaseURL)
	url = strings.ReplaceAll(url, "{season}", season)
	url = strings.ReplaceAll(url, "{league}", league)
	return url
}

// GetSourceMetadata returns metadata about a data source.
func (m *DataSourcesManager) GetSourceMetadata(sourceID string) map[string]any {
	src := m.GetSourceByID(sourceID)
	if src == nil {
		return nil
	}
	return map[string]any{
		"id":               src.ID,
		"name":             src.Name,
		"description":      src.Description,
		"type":             src.Type,
		"enabled":          src.Enabled,
		"requires_api_key": src.RequiresAPIKey,
		"sports":           src.Sports,
	}
}

// GetAllSourcesMetadata returns metadata for all sources.
func (m *DataSourcesManager) GetAllSourcesMetadata() []map[string]any {
	if m.Config == nil {
		return nil
	}
	var result []map[string]any
	for _, s := range m.Config.Sources {
		result = append(result, m.GetSourceMetadata(s.ID))
	}
	return result
}

// SaveConfig saves the current configuration back to file.
func (m *DataSourcesManager) SaveConfig() error {
	data, err := json.MarshalIndent(m.Config, "", "  ")
	if err != nil {
		return fmt.Errorf("marshaling config: %w", err)
	}
	if err := os.WriteFile(m.configPath, data, 0o644); err != nil {
		return fmt.Errorf("writing config %s: %w", m.configPath, err)
	}
	return nil
}

// EnableSource enables a data source.
func (m *DataSourcesManager) EnableSource(sourceID string) {
	if src := m.GetSourceByID(sourceID); src != nil {
		src.Enabled = true
	}
}

// DisableSource disables a data source.
func (m *DataSourcesManager) DisableSource(sourceID string) {
	if src := m.GetSourceByID(sourceID); src != nil {
		src.Enabled = false
	}
}
