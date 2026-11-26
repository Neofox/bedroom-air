package main

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"slices"
	"testing"
)

func TestHistoricalCurve(t *testing.T) {
	// With a fractional start the first available whole second is 1.
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/history" || r.URL.Query().Get("from") != "1" || r.URL.Query().Get("to") != "652" {
			t.Errorf("unexpected history request %s", r.URL)
		}
		w.Write([]byte(`[{"t":1,"co2":800,"temperature":21},{"t":300,"co2":901,"lux":0},{"t":601,"temperature":0},{"t":651,"co2":1050}]`))
	}))
	defer server.Close()
	base, _ := url.Parse(server.URL)
	d := dashboard{base, server.Client()}
	args := historicalArgs{StartTime: "1970-01-01T09:00:00.5+09:00", EndTime: "1970-01-01T00:10:51.5Z"}
	_, r, err := d.historical(t.Context(), nil, args)
	if err != nil {
		t.Fatal(err)
	}
	if r.Interval != 5 || r.StartTime != args.StartTime || r.EndTime != args.EndTime || !slices.Equal(r.SampleCount, []int{2, 0, 2}) {
		t.Fatalf("wrong time axis or row counts: %+v", r)
	}
	if len(r.CO2) != 3 || r.CO2[0] == nil || *r.CO2[0] != 850.5 || r.CO2[1] != nil || r.CO2[2] == nil || *r.CO2[2] != 1050 {
		t.Error("unexpected CO₂ curve")
	}
	if r.Lux[0] == nil || *r.Lux[0] != 0 || r.Lux[2] != nil || r.Temperature[2] == nil || *r.Temperature[2] != 0 || r.Humidity[0] != nil {
		t.Error("available values, zero readings and missing measurements should be distinct")
	}
}

func TestHistoricalValidatesRangeAndIntervalBeforeFetching(t *testing.T) {
	start := "2026-01-01T00:00:00Z"
	end := "2026-01-01T12:00:00Z"
	zero, tooLarge := 0, 2881
	for _, args := range []historicalArgs{
		{StartTime: "2026-01-01T00:00:00", EndTime: end},
		{StartTime: start, EndTime: "yesterday"},
		{StartTime: end, EndTime: start}, {StartTime: start, EndTime: start},
		{StartTime: start, EndTime: "2026-01-03T00:00:01Z"},
		{StartTime: start, EndTime: end, Interval: &zero}, {StartTime: start, EndTime: end, Interval: &tooLarge},
	} {
		if _, _, err := (dashboard{}).historical(t.Context(), nil, args); err == nil {
			t.Errorf("accepted invalid arguments %+v", args)
		}
	}
}
