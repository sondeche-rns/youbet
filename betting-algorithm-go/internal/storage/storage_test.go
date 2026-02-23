package storage

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCSVStoreReadWrite(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewCSVStore(tmpDir)

	matches := []MatchRecord{
		{
			Date: "2024-01-01", Season: "2023-24",
			HomeTeam: "Arsenal", AwayTeam: "Chelsea",
			HomeGoals: 2, AwayGoals: 1,
			HomeOdds: 1.80, DrawOdds: 3.40, AwayOdds: 4.50,
			HomeShots: 15, AwayShots: 10,
			HomeShotsOnTarget: 7, AwayShotsOnTarget: 4,
			MatchID: 1,
			HomeXG: 2.1, AwayXG: 0.9,
			HomeElo: 1800, AwayElo: 1690,
			HomeForm: "WWWWW", AwayForm: "WDLWW",
			HomeRestDays: 7, AwayRestDays: 5,
			HomeGamesLast7: 1, AwayGamesLast7: 2,
			HomePossession: 58.5, AwayPossession: 41.5,
			HomePPDA: 10.5, AwayPPDA: 12.3,
			HomePosition: 1, AwayPosition: 5,
		},
		{
			Date: "2024-01-02", Season: "2023-24",
			HomeTeam: "Liverpool", AwayTeam: "Man City",
			HomeGoals: 1, AwayGoals: 1,
			HomeOdds: 2.50, DrawOdds: 3.20, AwayOdds: 2.80,
			HomeShots: 12, AwayShots: 14,
			HomeShotsOnTarget: 5, AwayShotsOnTarget: 6,
			MatchID: 2,
			HomeXG: 1.5, AwayXG: 1.6,
			HomeElo: 1680, AwayElo: 1760,
			HomeForm: "WDLWW", AwayForm: "WLWWW",
			HomeRestDays: 4, AwayRestDays: 3,
			HomeGamesLast7: 2, AwayGamesLast7: 3,
			HomePossession: 45.0, AwayPossession: 55.0,
			HomePPDA: 11.2, AwayPPDA: 9.8,
			HomePosition: 6, AwayPosition: 2,
		},
	}

	filePath := filepath.Join(tmpDir, "test.csv")
	err := store.WriteHistoricalData(filePath, matches)
	if err != nil {
		t.Fatalf("WriteHistoricalData error: %v", err)
	}

	// Read back
	loaded, err := store.ReadHistoricalData(filePath)
	if err != nil {
		t.Fatalf("ReadHistoricalData error: %v", err)
	}

	if len(loaded) != 2 {
		t.Fatalf("expected 2 records, got %d", len(loaded))
	}

	if loaded[0].HomeTeam != "Arsenal" || loaded[0].AwayTeam != "Chelsea" {
		t.Errorf("first record teams mismatch: %s vs %s", loaded[0].HomeTeam, loaded[0].AwayTeam)
	}
	if loaded[0].HomeGoals != 2 || loaded[0].AwayGoals != 1 {
		t.Errorf("first record goals mismatch: %d-%d", loaded[0].HomeGoals, loaded[0].AwayGoals)
	}
	if loaded[1].HomeTeam != "Liverpool" {
		t.Errorf("second record home team should be Liverpool, got %s", loaded[1].HomeTeam)
	}
}

func TestCSVStoreReadMissingFile(t *testing.T) {
	store := NewCSVStore(t.TempDir())
	_, err := store.ReadHistoricalData("/nonexistent/file.csv")
	if err == nil {
		t.Error("expected error for missing file")
	}
}

func TestJSONStoreSaveLoad(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	type TestData struct {
		Name  string `json:"name"`
		Value int    `json:"value"`
	}

	original := TestData{Name: "test", Value: 42}
	filePath := filepath.Join(tmpDir, "test.json")

	err := store.Save(filePath, original)
	if err != nil {
		t.Fatalf("Save error: %v", err)
	}

	var loaded TestData
	err = store.Load(filePath, &loaded)
	if err != nil {
		t.Fatalf("Load error: %v", err)
	}

	if loaded.Name != original.Name || loaded.Value != original.Value {
		t.Errorf("loaded data mismatch: got %+v, want %+v", loaded, original)
	}
}

func TestJSONStoreExists(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	filePath := filepath.Join(tmpDir, "exists.json")
	if store.Exists(filePath) {
		t.Error("file should not exist yet")
	}

	if err := os.WriteFile(filePath, []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}
	if !store.Exists(filePath) {
		t.Error("file should exist after creation")
	}
}

func TestJSONStoreNestedDir(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	filePath := filepath.Join(tmpDir, "sub", "dir", "data.json")
	err := store.Save(filePath, map[string]string{"key": "value"})
	if err != nil {
		t.Fatalf("Save to nested dir should work: %v", err)
	}

	if !store.Exists(filePath) {
		t.Error("file should exist in nested directory")
	}
}

func TestJSONStorePrediction(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	pred := PredictionRecord{
		ID:             "pred-001",
		HomeTeam:       "Arsenal",
		AwayTeam:       "Chelsea",
		HomeWinProb:    0.55,
		DrawProb:       0.25,
		AwayWinProb:    0.20,
		Confidence:     78.5,
		Recommendation: "HOME",
		Timestamp:      "2026-02-20T10:00:00Z",
	}

	filePath := filepath.Join(tmpDir, "prediction.json")
	err := store.SavePrediction(filePath, pred)
	if err != nil {
		t.Fatalf("SavePrediction error: %v", err)
	}

	loaded, err := store.LoadPrediction(filePath)
	if err != nil {
		t.Fatalf("LoadPrediction error: %v", err)
	}

	if loaded.ID != pred.ID || loaded.HomeTeam != pred.HomeTeam {
		t.Errorf("prediction mismatch: got %+v", loaded)
	}
	if loaded.HomeWinProb != pred.HomeWinProb {
		t.Errorf("HomeWinProb mismatch: got %f, want %f", loaded.HomeWinProb, pred.HomeWinProb)
	}
}
