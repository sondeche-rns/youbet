package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// JSONStore handles reading and writing JSON files.
type JSONStore struct {
	DataDir string
}

// NewJSONStore creates a new JSONStore with the given data directory.
func NewJSONStore(dataDir string) *JSONStore {
	return &JSONStore{DataDir: dataDir}
}

// Save writes a value as JSON to the given file path.
func (s *JSONStore) Save(filePath string, v any) error {
	dir := filepath.Dir(filePath)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("creating directory %s: %w", dir, err)
	}

	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshaling JSON: %w", err)
	}

	if err := os.WriteFile(filePath, data, 0o644); err != nil {
		return fmt.Errorf("writing file %s: %w", filePath, err)
	}

	return nil
}

// Load reads JSON from a file into the given pointer.
func (s *JSONStore) Load(filePath string, v any) error {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("reading file %s: %w", filePath, err)
	}

	if err := json.Unmarshal(data, v); err != nil {
		return fmt.Errorf("unmarshaling JSON from %s: %w", filePath, err)
	}

	return nil
}

// Exists checks if a file exists.
func (s *JSONStore) Exists(filePath string) bool {
	_, err := os.Stat(filePath)
	return err == nil
}

// ManagerEntry represents a manager record from managers.json.
type ManagerEntry struct {
	Team            string   `json:"team"`
	Name            string   `json:"name"`
	AppointmentDate string   `json:"appointmentDate"`
	GamesManaged    int      `json:"gamesManaged"`
	Results         []string `json:"results"`
	IsInterim       bool     `json:"isInterim"`
}

// LoadManagers reads the managers.json file.
func (s *JSONStore) LoadManagers(filePath string) ([]ManagerEntry, error) {
	var managers []ManagerEntry
	if err := s.Load(filePath, &managers); err != nil {
		return nil, err
	}
	return managers, nil
}

// DataSource represents a data source entry from data_sources.json.
type DataSource struct {
	Name        string `json:"name"`
	URL         string `json:"url"`
	Sport       string `json:"sport"`
	League      string `json:"league"`
	Country     string `json:"country"`
	Seasons     []string `json:"seasons"`
	DataType    string `json:"data_type"`
	Description string `json:"description"`
}

// DataSourcesConfig holds the data_sources.json structure.
type DataSourcesConfig struct {
	Sources []DataSource `json:"sources"`
}

// LoadDataSources reads the data_sources.json config file.
func (s *JSONStore) LoadDataSources(filePath string) (*DataSourcesConfig, error) {
	var config DataSourcesConfig
	if err := s.Load(filePath, &config); err != nil {
		return nil, err
	}
	return &config, nil
}

// PredictionRecord represents a saved prediction.
type PredictionRecord struct {
	ID             string         `json:"id"`
	HomeTeam       string         `json:"home_team"`
	AwayTeam       string         `json:"away_team"`
	HomeWinProb    float64        `json:"homeWinProb"`
	DrawProb       float64        `json:"drawProb"`
	AwayWinProb    float64        `json:"awayWinProb"`
	Confidence     float64        `json:"confidence"`
	Recommendation string         `json:"recommendation"`
	Timestamp      string         `json:"timestamp"`
	Metadata       map[string]any `json:"metadata,omitempty"`
}

// SavePrediction saves a prediction record.
func (s *JSONStore) SavePrediction(filePath string, pred PredictionRecord) error {
	return s.Save(filePath, pred)
}

// LoadPrediction loads a prediction record.
func (s *JSONStore) LoadPrediction(filePath string) (*PredictionRecord, error) {
	var pred PredictionRecord
	if err := s.Load(filePath, &pred); err != nil {
		return nil, err
	}
	return &pred, nil
}

// ListFiles returns all files matching a pattern in a directory.
func (s *JSONStore) ListFiles(dir, pattern string) ([]string, error) {
	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil {
		return nil, fmt.Errorf("listing files in %s: %w", dir, err)
	}
	return matches, nil
}
