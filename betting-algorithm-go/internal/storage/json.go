package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// JSONStore handles reading and writing JSON data files.
type JSONStore struct {
	DataDir string
}

// NewJSONStore creates a new JSON store rooted at the given data directory.
func NewJSONStore(dataDir string) *JSONStore {
	return &JSONStore{DataDir: dataDir}
}

// Save writes a value as JSON to the given file path (relative to DataDir).
func (s *JSONStore) Save(filename string, v any) error {
	path := filepath.Join(s.DataDir, filename)

	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}

	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}

	if err := os.WriteFile(path, data, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}

// Load reads a JSON file into the provided target.
func (s *JSONStore) Load(filename string, target any) error {
	path := filepath.Join(s.DataDir, filename)

	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read %s: %w", path, err)
	}

	if err := json.Unmarshal(data, target); err != nil {
		return fmt.Errorf("unmarshal %s: %w", path, err)
	}
	return nil
}

// Exists checks if a JSON file exists.
func (s *JSONStore) Exists(filename string) bool {
	path := filepath.Join(s.DataDir, filename)
	_, err := os.Stat(path)
	return err == nil
}

// List returns all files matching a pattern in a subdirectory.
func (s *JSONStore) List(subdir, pattern string) ([]string, error) {
	dir := filepath.Join(s.DataDir, subdir)

	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("readdir %s: %w", dir, err)
	}

	var result []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		matched, err := filepath.Match(pattern, entry.Name())
		if err != nil {
			return nil, fmt.Errorf("match pattern %s: %w", pattern, err)
		}
		if matched {
			result = append(result, entry.Name())
		}
	}
	return result, nil
}

// Delete removes a file.
func (s *JSONStore) Delete(filename string) error {
	path := filepath.Join(s.DataDir, filename)
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove %s: %w", path, err)
	}
	return nil
}

// DataSourceConfig represents the structure of config/data_sources.json.
type DataSourceConfig struct {
	Sources map[string]DataSource `json:"sources"`
}

// DataSource represents a single data source configuration.
type DataSource struct {
	Name     string            `json:"name"`
	Type     string            `json:"type"`
	BaseURL  string            `json:"base_url,omitempty"`
	Enabled  bool              `json:"enabled"`
	Leagues  map[string]string `json:"leagues,omitempty"`
	Seasons  []string          `json:"seasons,omitempty"`
	Timeout  int               `json:"timeout,omitempty"`
	RateLimit float64          `json:"rate_limit,omitempty"`
}

// LoadDataSources reads the data sources configuration from a JSON file.
func LoadDataSources(path string) (*DataSourceConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}

	var config DataSourceConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("unmarshal %s: %w", path, err)
	}
	return &config, nil
}

// ManagerDatabase represents the managers.json structure.
type ManagerDatabase map[string]ManagerEntry

// ManagerEntry represents a single team's manager info in the JSON file.
type ManagerEntry struct {
	Name            string   `json:"name"`
	AppointmentDate string   `json:"appointmentDate"`
	GamesManaged    int      `json:"gamesManaged"`
	Results         []string `json:"results"`
	IsInterim       bool     `json:"isInterim"`
}

// LoadManagers reads the manager database from a JSON file.
func LoadManagers(path string) (ManagerDatabase, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return make(ManagerDatabase), nil
		}
		return nil, fmt.Errorf("read %s: %w", path, err)
	}

	var db ManagerDatabase
	if err := json.Unmarshal(data, &db); err != nil {
		return nil, fmt.Errorf("unmarshal %s: %w", path, err)
	}
	return db, nil
}

// SaveManagers writes the manager database to a JSON file.
func SaveManagers(path string, db ManagerDatabase) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}

	data, err := json.MarshalIndent(db, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}

	if err := os.WriteFile(path, data, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}

// SanitizeFilename removes unsafe characters from a filename.
func SanitizeFilename(name string) string {
	replacer := strings.NewReplacer(
		"/", "_",
		"\\", "_",
		":", "_",
		"*", "_",
		"?", "_",
		"\"", "_",
		"<", "_",
		">", "_",
		"|", "_",
	)
	return replacer.Replace(name)
}
