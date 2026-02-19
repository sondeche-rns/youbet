package storage

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCSVStore_WriteAndRead(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewCSVStore(tmpDir)

	records := []MatchRecord{
		{
			Date: "2024-01-15", HomeTeam: "Arsenal", AwayTeam: "Chelsea",
			HomeGoals: 2, AwayGoals: 1, HomeOdds: 1.8, DrawOdds: 3.5, AwayOdds: 4.2,
			HomeXG: 2.1, AwayXG: 0.9, HomeElo: 1800, AwayElo: 1690,
			HomeForm: "WWDWW", AwayForm: "WWDLW", HomePos: 1, AwayPos: 5,
			Season: "2324", League: "E0", RestDaysH: 4, RestDaysA: 3, Result: "H",
		},
		{
			Date: "2024-01-16", HomeTeam: "Liverpool", AwayTeam: "Man City",
			HomeGoals: 1, AwayGoals: 1, HomeOdds: 2.5, DrawOdds: 3.3, AwayOdds: 2.7,
			HomeXG: 1.5, AwayXG: 1.4, HomeElo: 1680, AwayElo: 1760,
			HomeForm: "WDLWW", AwayForm: "WLWWW", HomePos: 6, AwayPos: 2,
			Season: "2324", League: "E0", RestDaysH: 5, RestDaysA: 6, Result: "D",
		},
	}

	err := store.WriteHistoricalData("final/test_data.csv", records)
	if err != nil {
		t.Fatalf("WriteHistoricalData() error: %v", err)
	}

	// Verify file exists
	if !store.Exists("final/test_data.csv") {
		t.Fatal("file should exist after write")
	}

	// Read back
	got, err := store.ReadHistoricalData("final/test_data.csv")
	if err != nil {
		t.Fatalf("ReadHistoricalData() error: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("got %d records, want 2", len(got))
	}

	// Verify first record
	r := got[0]
	if r.HomeTeam != "Arsenal" {
		t.Errorf("HomeTeam = %q, want %q", r.HomeTeam, "Arsenal")
	}
	if r.AwayTeam != "Chelsea" {
		t.Errorf("AwayTeam = %q, want %q", r.AwayTeam, "Chelsea")
	}
	if r.HomeGoals != 2 {
		t.Errorf("HomeGoals = %d, want 2", r.HomeGoals)
	}
	if r.Result != "H" {
		t.Errorf("Result = %q, want %q", r.Result, "H")
	}
	if r.HomeOdds != 1.8 {
		t.Errorf("HomeOdds = %f, want 1.8", r.HomeOdds)
	}
}

func TestCSVStore_ReadNonExistent(t *testing.T) {
	store := NewCSVStore(t.TempDir())
	_, err := store.ReadHistoricalData("does_not_exist.csv")
	if err == nil {
		t.Error("expected error for non-existent file")
	}
}

func TestCSVStore_Exists(t *testing.T) {
	store := NewCSVStore(t.TempDir())
	if store.Exists("nonexistent.csv") {
		t.Error("expected false for non-existent file")
	}
}

func TestJSONStore_SaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	type TestData struct {
		Name  string  `json:"name"`
		Value float64 `json:"value"`
	}

	original := TestData{Name: "test", Value: 42.5}
	err := store.Save("test.json", original)
	if err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	if !store.Exists("test.json") {
		t.Fatal("file should exist after save")
	}

	var loaded TestData
	err = store.Load("test.json", &loaded)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}
	if loaded.Name != original.Name || loaded.Value != original.Value {
		t.Errorf("loaded = %+v, want %+v", loaded, original)
	}
}

func TestJSONStore_SaveToSubdir(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	err := store.Save("subdir/nested/data.json", map[string]string{"key": "value"})
	if err != nil {
		t.Fatalf("Save() to subdir error: %v", err)
	}

	if !store.Exists("subdir/nested/data.json") {
		t.Fatal("file in subdir should exist after save")
	}
}

func TestJSONStore_LoadNonExistent(t *testing.T) {
	store := NewJSONStore(t.TempDir())
	var data map[string]any
	err := store.Load("nonexistent.json", &data)
	if err == nil {
		t.Error("expected error for non-existent file")
	}
}

func TestJSONStore_List(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	// Create some files
	subdir := filepath.Join(tmpDir, "predictions")
	os.MkdirAll(subdir, 0o755)
	os.WriteFile(filepath.Join(subdir, "pred_001.json"), []byte("{}"), 0o644)
	os.WriteFile(filepath.Join(subdir, "pred_002.json"), []byte("{}"), 0o644)
	os.WriteFile(filepath.Join(subdir, "other.txt"), []byte(""), 0o644)

	files, err := store.List("predictions", "pred_*.json")
	if err != nil {
		t.Fatalf("List() error: %v", err)
	}
	if len(files) != 2 {
		t.Errorf("List() returned %d files, want 2", len(files))
	}
}

func TestJSONStore_ListNonExistentDir(t *testing.T) {
	store := NewJSONStore(t.TempDir())
	files, err := store.List("nonexistent", "*.json")
	if err != nil {
		t.Fatalf("List() error: %v", err)
	}
	if files != nil {
		t.Errorf("List() for non-existent dir should return nil, got %v", files)
	}
}

func TestJSONStore_Delete(t *testing.T) {
	tmpDir := t.TempDir()
	store := NewJSONStore(tmpDir)

	store.Save("delete_me.json", map[string]any{"test": true})
	if !store.Exists("delete_me.json") {
		t.Fatal("file should exist before delete")
	}

	err := store.Delete("delete_me.json")
	if err != nil {
		t.Fatalf("Delete() error: %v", err)
	}

	if store.Exists("delete_me.json") {
		t.Error("file should not exist after delete")
	}
}

func TestJSONStore_DeleteNonExistent(t *testing.T) {
	store := NewJSONStore(t.TempDir())
	err := store.Delete("nonexistent.json")
	if err != nil {
		t.Errorf("Delete() non-existent should not error, got: %v", err)
	}
}

func TestLoadManagers_NonExistent(t *testing.T) {
	db, err := LoadManagers("/tmp/nonexistent_managers_test.json")
	if err != nil {
		t.Fatalf("LoadManagers() should return empty for non-existent, got error: %v", err)
	}
	if len(db) != 0 {
		t.Errorf("expected empty map, got %d entries", len(db))
	}
}

func TestSaveAndLoadManagers(t *testing.T) {
	path := filepath.Join(t.TempDir(), "managers.json")

	db := ManagerDatabase{
		"Arsenal": {
			Name: "Arteta", AppointmentDate: "2019-12-20",
			GamesManaged: 180, Results: []string{"W", "W", "D"},
		},
	}

	err := SaveManagers(path, db)
	if err != nil {
		t.Fatalf("SaveManagers() error: %v", err)
	}

	loaded, err := LoadManagers(path)
	if err != nil {
		t.Fatalf("LoadManagers() error: %v", err)
	}
	if len(loaded) != 1 {
		t.Fatalf("loaded %d entries, want 1", len(loaded))
	}
	if loaded["Arsenal"].Name != "Arteta" {
		t.Errorf("Name = %q, want %q", loaded["Arsenal"].Name, "Arteta")
	}
}

func TestSanitizeFilename(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"normal.json", "normal.json"},
		{"path/with/slashes", "path_with_slashes"},
		{"bad:chars*here?", "bad_chars_here_"},
	}
	for _, tt := range tests {
		got := SanitizeFilename(tt.input)
		if got != tt.want {
			t.Errorf("SanitizeFilename(%q) = %q, want %q", tt.input, got, tt.want)
		}
	}
}
