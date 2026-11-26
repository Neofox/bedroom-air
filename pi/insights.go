package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"math"
	"net/http"
	"slices"
	"sort"
	"strconv"
	"time"
)

const maxSampleGap = 100 // seconds, shared with the history chart

func savedReadings(ctx context.Context, db *sql.DB, from, to int64) ([]reading, error) {
	rows, err := db.QueryContext(ctx, "SELECT t,co2,temperature,humidity,lux FROM readings WHERE t>=? AND t<? ORDER BY t", from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	data := make([]reading, 0)
	for rows.Next() {
		var r reading
		if err = rows.Scan(&r.Time, &r.CO2, &r.Temperature, &r.Humidity, &r.Lux); err != nil {
			return nil, err
		}
		data = append(data, r)
	}
	return data, rows.Err()
}

func nightWindow(pick string, now time.Time) (time.Time, time.Time, error) {
	year, month, date := now.Date()
	start := time.Date(year, month, date, 20, 0, 0, 0, now.Location())
	if start.After(now) {
		start = start.AddDate(0, 0, -1)
	}
	switch pick {
	case "", "last":
		if now.Before(nightEnd(start)) {
			start = start.AddDate(0, 0, -1)
		}
	case "latest":
	default:
		d, err := time.ParseInLocation(time.DateOnly, pick, now.Location())
		if err != nil {
			return time.Time{}, time.Time{}, err
		}
		year, month, date = d.Date()
		requested := time.Date(year, month, date, 20, 0, 0, 0, now.Location())
		if requested.After(start) {
			return time.Time{}, time.Time{}, errors.New("future night")
		}
		start = requested
	}
	return start, nightEnd(start), nil
}

func nightEnd(start time.Time) time.Time {
	y, m, d := start.AddDate(0, 0, 1).Date()
	return time.Date(y, m, d, 8, 0, 0, 0, start.Location())
}

func within(rows []reading, from, to int64) []reading {
	index := func(t int64) int { return sort.Search(len(rows), func(i int) bool { return rows[i].Time >= t }) }
	return rows[index(from):index(to)]
}

type nightStats struct {
	Peak    int   `json:"peak"`
	PeakAt  int64 `json:"peakAt"`
	Above   int64 `json:"above"`
	Covered int64 `json:"covered"`
	Count   int   `json:"count"`
}

// Integrate between adjacent measurements, splitting a threshold crossing
// linearly. Gaps and the unobserved ends of a night contribute no duration.
func summarizeNight(rows []reading, threshold int) nightStats {
	var s nightStats
	var above float64
	for i, r := range rows {
		if r.CO2 == nil {
			continue
		}
		s.Count++
		value := *r.CO2
		if value > s.Peak {
			s.Peak = value
			s.PeakAt = r.Time
		}
		if i == 0 || rows[i-1].CO2 == nil {
			continue
		}
		prev := rows[i-1]
		dt := r.Time - prev.Time
		if dt <= 0 || dt > maxSampleGap {
			continue
		}
		s.Covered += dt
		lo, hi := min(*prev.CO2, value), max(*prev.CO2, value)
		switch {
		case lo >= threshold:
			above += float64(dt)
		case hi > threshold:
			above += float64(dt) * float64(hi-threshold) / float64(hi-lo)
		}
	}
	s.Above = int64(math.Round(above))
	return s
}

func nightReport(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		now := time.Now()
		q := r.URL.Query()
		start, end, err := nightWindow(q.Get("night"), now)
		threshold := 1500
		if v := q.Get("threshold"); v != "" {
			n, e := strconv.Atoi(v)
			if e != nil || n < 400 || n > 5000 {
				http.Error(w, "Choose a CO₂ level from 400 to 5000 ppm.", 400)
				return
			}
			threshold = n
		}
		if err != nil {
			http.Error(w, "Choose a night that has already started.", 400)
			return
		}
		all, err := savedReadings(r.Context(), db, start.AddDate(0, 0, -7).Unix(), min(now.Unix()+1, end.Unix()))
		if err != nil {
			http.Error(w, "Night history unavailable", 500)
			return
		}
		rows := within(all, start.Unix(), end.Unix())
		s := summarizeNight(rows, threshold)
		peaks := []int{}
		for i := 1; i <= 7; i++ {
			a := start.AddDate(0, 0, -i)
			b := nightEnd(a)
			prior := summarizeNight(within(all, a.Unix(), b.Unix()), threshold)
			if float64(prior.Covered) >= .8*b.Sub(a).Seconds() {
				peaks = append(peaks, prior.Peak)
			}
		}
		var typical *int
		if len(peaks) >= 3 {
			slices.Sort(peaks)
			n := len(peaks)
			median := (peaks[(n-1)/2] + peaks[n/2] + 1) / 2
			typical = &median
		}
		latest, _, _ := nightWindow("latest", now)
		last, _, _ := nightWindow("last", now)
		writeReport(w, map[string]any{"start": start.Unix(), "end": end.Unix(), "asOf": now.Unix(), "date": start.Format(time.DateOnly),
			"last": last.Format(time.DateOnly), "latest": latest.Format(time.DateOnly), "stats": s, "threshold": threshold,
			"comparisonNights": len(peaks), "typicalPeak": typical, "samples": rows})
	}
}

type airEvent struct {
	Start       int64    `json:"start"`
	End         int64    `json:"end"`
	StartCO2    int      `json:"startCO2"`
	EndCO2      int      `json:"endCO2"`
	Drop        int      `json:"drop"`
	StartTemp   *float64 `json:"startTemp"`
	EndTemp     *float64 `json:"endTemp"`
	MinTemp     *float64 `json:"minTemp"`
	Recovery    string   `json:"recovery"`
	RecoveredAt int64    `json:"recoveredAt,omitempty"`
	Ongoing     bool     `json:"ongoing,omitempty"`
}

func median3(a, b, c int) int { return max(min(a, b), min(max(a, b), c)) }

type dropSpan struct {
	start, end int
	ongoing    bool
}

// Work on a contiguous run of CO₂ measurements. A three-point median rejects
// single-sample spikes. A sustained drop needs at least three downward steps.
func findDrops(run []reading, asOf int64) []dropSpan {
	smoothed := make([]int, len(run))
	for i := range run {
		smoothed[i] = median3(*run[max(0, i-1)].CO2, *run[i].CO2, *run[min(len(run)-1, i+1)].CO2)
	}
	var spans []dropSpan
	floor := 1 // require a real neighbour on either side for the median
	for i := 2; i < len(run)-1; i++ {
		if smoothed[i] >= smoothed[i-1] {
			continue
		}
		start := i
		for j := i - 1; j >= floor && run[i].Time-run[j].Time <= 30*60; j-- {
			if smoothed[j] > smoothed[start] {
				start = j
			}
		}
		if run[i].Time-run[start].Time < 5*60 || smoothed[start]-smoothed[i] < 150 {
			continue
		}
		down := 0
		for j := start + 1; j <= i; j++ {
			if smoothed[j] < smoothed[j-1] {
				down++
			}
		}
		if down < 3 {
			continue
		}
		bottom := i
		j := i + 1
		for ; j < len(run)-1; j++ {
			if run[j].Time-run[bottom].Time > 4*60 || smoothed[j]-smoothed[bottom] >= 45 {
				break
			}
			if smoothed[j] < smoothed[bottom] {
				bottom = j
			}
		}
		open := j == len(run)-1 && asOf-run[bottom].Time <= 4*60
		spans = append(spans, dropSpan{start, bottom, open})
		floor = bottom + 1
		i = bottom
	}
	return spans
}

func describeDrop(run []reading, span dropSpan, stop int, asOf int64) airEvent {
	a, b := span.start, span.end
	level := func(i int) int { return median3(*run[i-1].CO2, *run[i].CO2, *run[i+1].CO2) }
	e := airEvent{Start: run[a].Time, End: run[b].Time, StartCO2: level(a), EndCO2: level(b), StartTemp: run[a].Temperature,
		EndTemp: run[b].Temperature, Ongoing: span.ongoing, Recovery: "unavailable"}
	e.Drop = e.StartCO2 - e.EndCO2
	if e.StartTemp == nil {
		return e
	}
	lowest := *e.StartTemp
	for _, r := range run[a : b+1] {
		if r.Temperature == nil {
			return e
		}
		lowest = min(lowest, *r.Temperature)
	}
	e.MinTemp = &lowest
	if e.Ongoing {
		e.Recovery = "ongoing"
		return e
	}
	if math.Round((*e.StartTemp-lowest)*10) < 3 {
		e.Recovery = "steady"
		return e
	}
	var streak int
	for i := b; i < stop && run[i].Time-e.End <= 2*3600; i++ {
		if run[i].Temperature == nil {
			return e
		}
		if *run[i].Temperature >= *e.StartTemp-0.20001 {
			streak++
			if streak == 3 {
				e.Recovery = "returned"
				e.RecoveredAt = run[i-2].Time
				return e
			}
		} else {
			streak = 0
		}
	}
	e.Recovery = "unconfirmed"
	if stop == len(run) && asOf-e.End < 2*3600 && asOf-run[stop-1].Time <= maxSampleGap {
		e.Recovery = "watching"
	}
	return e
}

func detectAiring(rows []reading, asOf int64) []airEvent {
	events := make([]airEvent, 0)
	for i := 0; i < len(rows); {
		if rows[i].CO2 == nil {
			i++
			continue
		}
		j := i + 1
		for j < len(rows) && rows[j].CO2 != nil && rows[j].Time-rows[j-1].Time <= maxSampleGap {
			j++
		}
		run := rows[i:j]
		spans := findDrops(run, asOf)
		for k, span := range spans {
			stop := len(run)
			if k+1 < len(spans) {
				stop = spans[k+1].start
			}
			events = append(events, describeDrop(run, span, stop, asOf))
		}
		i = j
	}
	return events
}

func airingReport(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		hours := 24
		switch r.URL.Query().Get("hours") {
		case "", "24":
		case "168":
			hours = 168
		default:
			http.Error(w, "Choose 24 hours or 7 days.", 400)
			return
		}
		now := time.Now().Unix()
		start := now - int64(hours)*3600
		rows, err := savedReadings(r.Context(), db, start-2*3600, now+1)
		if err != nil {
			http.Error(w, "Airing history unavailable", 500)
			return
		}
		all := detectAiring(rows, now)
		events := make([]airEvent, 0)
		for i := len(all) - 1; i >= 0; i-- {
			if all[i].End >= start {
				events = append(events, all[i])
			}
		}
		s := summarizeNight(within(rows, start, now+1), 1500)
		writeReport(w, map[string]any{"start": start, "asOf": now, "covered": s.Covered, "events": events})
	}
}

func writeReport(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	json.NewEncoder(w).Encode(v)
}
