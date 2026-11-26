package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
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
	if r.Interval != 5 || r.StartTime != args.StartTime || r.EndTime != args.EndTime {
		t.Fatalf("wrong time range: %+v", r)
	}
	b, err := json.Marshal(r.Readings)
	if err != nil {
		t.Fatal(err)
	}
	const want = `[{"t":"1970-01-01T09:00:00.5+09:00","n":2,"co2":850.5,"temperature":21,"humidity":null,"lux":0},{"t":"1970-01-01T09:05:00.5+09:00","n":0,"co2":null,"temperature":null,"humidity":null,"lux":null},{"t":"1970-01-01T09:10:00.5+09:00","n":2,"co2":1050,"temperature":0,"humidity":null,"lux":null}]`
	if string(b) != want {
		t.Errorf("unexpected timestamped curve: %s", b)
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
