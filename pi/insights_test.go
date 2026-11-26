package main

import (
	"testing"
	"time"
)

func sample(t int64, c int, temp float64) reading {
	return reading{Time: t, CO2: &c, Temperature: &temp}
}

func TestNightTimes(t *testing.T) {
	kst := time.FixedZone("KST", 9*3600)
	for _, tc := range []struct {
		hour         int
		last, latest string
	}{
		{2, "2026-11-24", "2026-11-25"}, {8, "2026-11-25", "2026-11-25"}, {22, "2026-11-25", "2026-11-26"},
	} {
		now := time.Date(2026, 11, 26, tc.hour, 0, 0, 0, kst)
		for pick, want := range map[string]string{"last": tc.last, "latest": tc.latest} {
			start, end, err := nightWindow(pick, now)
			if err != nil || start.Format(time.DateOnly) != want || start.Hour() != 20 || end.Hour() != 8 || end.Sub(start) != 12*time.Hour {
				t.Fatalf("%d %s: %v to %v (%v)", tc.hour, pick, start, end, err)
			}
		}
	}
}

func TestNightCoverage(t *testing.T) {
	rows := []reading{sample(100, 1400, 21), sample(160, 1600, 21), sample(220, 1600, 21), {Time: 280}, sample(500, 2000, 21), sample(560, 1400, 21)}
	s := summarizeNight(rows, 1500)
	if s.Covered != 180 || s.Above != 140 || s.Peak != 2000 || s.PeakAt != 500 {
		t.Fatalf("%+v", s)
	}
}

func TestAiringAndRecovery(t *testing.T) {
	var rows []reading
	for i := 0; i < 45; i++ {
		ppm, temp := 1500, 22.0
		if i > 4 {
			steps := min(i-4, 9)
			ppm -= steps * 30
			temp -= float64(steps) / 10
		}
		if i >= 20 {
			temp = 22
		}
		rows = append(rows, sample(int64(i*60), ppm, temp))
	}
	events := detectAiring(rows, 44*60)
	if len(events) != 1 {
		t.Fatalf("events %v", events)
	}
	e := events[0]
	if e.Start != 4*60 || e.End != 13*60 || e.Drop != 270 || e.Recovery != "returned" || e.RecoveredAt != 20*60 || e.MinTemp == nil || *e.MinTemp != 21.1 {
		t.Fatalf("unexpected result %+v", e)
	}
	rows[8].CO2 = nil
	if events := detectAiring(rows, 44*60); len(events) != 0 {
		t.Fatalf("joined separate runs: %+v", events)
	}
}

func TestAiringNoiseAndMissingTemperature(t *testing.T) {
	var rows []reading
	for i := 0; i < 21; i++ {
		rows = append(rows, sample(int64(i*60), 1200, 22))
	}
	*rows[5].CO2 = 1800
	if found := detectAiring(rows, 20*60); len(found) != 0 {
		t.Fatalf("single spike detected: %+v", found)
	}
	for i := range rows {
		*rows[i].CO2 = 1600 - min(i, 10)*25
		rows[i].Temperature = nil
	}
	found := detectAiring(rows, 20*60)
	if len(found) != 1 || found[0].Recovery != "unavailable" || found[0].MinTemp != nil {
		t.Fatalf("missing DHT data: %+v", found)
	}
}

func TestQuickDropFollowedByFlatReadings(t *testing.T) {
	var rows []reading
	for i := 0; i < 18; i++ {
		steps := max(0, min(i-4, 3))
		rows = append(rows, sample(int64(i*60), 1400-steps*70, 22))
	}
	if events := detectAiring(rows, 17*60); len(events) > 0 {
		t.Fatal("a three-minute fall followed by a plateau counted as sustained")
	}
}
