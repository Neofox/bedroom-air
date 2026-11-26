// bedroom-air-mcp reads the Pi's dashboard API over the LAN for a local MCP client.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type dashboard struct {
	base   *url.URL
	client *http.Client
}

func (d dashboard) get(ctx context.Context, path string, query url.Values, target any) error {
	endpoint := d.base.JoinPath("api", path)
	endpoint.RawQuery = query.Encode()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
	if err != nil {
		return err
	}
	res, err := d.client.Do(req)
	if err != nil {
		return fmt.Errorf("could not reach the Pi dashboard: %w", err)
	}
	defer res.Body.Close()
	if res.StatusCode == http.StatusServiceUnavailable && path == "live" {
		return errors.New("the Pi is reachable but the bedroom sensor is offline")
	}
	if res.StatusCode != http.StatusOK {
		return fmt.Errorf("dashboard %s returned HTTP %d", path, res.StatusCode)
	}
	return json.NewDecoder(io.LimitReader(res.Body, 2<<20)).Decode(target)
}

type sample struct {
	Time        int64    `json:"t"`
	CO2         *int     `json:"co2"`
	Temperature *float64 `json:"temperature"`
	Humidity    *float64 `json:"humidity"`
	Lux         *float64 `json:"lux"`
	Status      string   `json:"status,omitempty"`
}

type liveReading struct {
	ObservedAt  string   `json:"observed_at"`
	CO2         *int     `json:"co2_ppm"`
	Temperature *float64 `json:"temperature_c"`
	Humidity    *float64 `json:"relative_humidity_percent"`
	Lux         *float64 `json:"light_lux"`
	Status      string   `json:"sensor_status"`
}

func (d dashboard) live(ctx context.Context, _ *mcp.CallToolRequest, _ struct{}) (*mcp.CallToolResult, liveReading, error) {
	var s sample
	if err := d.get(ctx, "live", nil, &s); err != nil {
		return nil, liveReading{}, err
	}
	age := time.Since(time.Unix(s.Time, 0))
	if age > 30*time.Second || age < -30*time.Second {
		return nil, liveReading{}, errors.New("live timestamp is stale or outside clock tolerance; check the Pi and Mac clocks")
	}
	return nil, liveReading{time.Unix(s.Time, 0).Format(time.RFC3339), s.CO2, s.Temperature, s.Humidity, s.Lux, s.Status}, nil
}

type historyArgs struct {
	Minutes *int `json:"minutes,omitempty" jsonschema:"Minutes to look back (1–120; default 15)."`
}

type historyResult struct {
	From    int64    `json:"from"`
	To      int64    `json:"to_exclusive"`
	Samples []sample `json:"samples"`
}

func (d dashboard) recent(ctx context.Context, _ *mcp.CallToolRequest, args historyArgs) (*mcp.CallToolResult, historyResult, error) {
	minutes := 15
	if args.Minutes != nil {
		minutes = *args.Minutes
	}
	if minutes < 1 || minutes > 120 {
		return nil, historyResult{}, errors.New("choose 1 to 120 minutes")
	}
	to := time.Now().Unix() + 1
	from := to - int64(minutes)*60
	samples, err := d.savedReadings(ctx, from, to)
	return nil, historyResult{From: from, To: to, Samples: samples}, err
}

func (d dashboard) savedReadings(ctx context.Context, from, to int64) ([]sample, error) {
	query := url.Values{"from": {strconv.FormatInt(from, 10)}, "to": {strconv.FormatInt(to, 10)}}
	rows := []sample{}
	err := d.get(ctx, "history", query, &rows)
	return rows, err
}

type nightArgs struct {
	Night     string `json:"night,omitempty" jsonschema:"last (default) for the last completed night; latest for the most recently started night; or a start date YYYY-MM-DD in the Pi's timezone."`
	Threshold *int   `json:"threshold_ppm,omitempty" jsonschema:"CO₂ threshold in ppm from 400 to 5000 (default 1500)."`
}

type report = map[string]any

func (d dashboard) night(ctx context.Context, _ *mcp.CallToolRequest, args nightArgs) (*mcp.CallToolResult, report, error) {
	query := url.Values{"night": {args.Night}}
	switch args.Night {
	case "", "last", "latest":
	default:
		if _, err := time.Parse(time.DateOnly, args.Night); err != nil {
			return nil, nil, errors.New("choose last, latest, or a start date YYYY-MM-DD")
		}
	}
	if args.Threshold != nil {
		if *args.Threshold < 400 || *args.Threshold > 5000 {
			return nil, nil, errors.New("choose a threshold from 400 to 5000 ppm")
		}
		query.Set("threshold", strconv.Itoa(*args.Threshold))
	}
	var r report
	if err := d.get(ctx, "night", query, &r); err != nil {
		return nil, nil, err
	}
	delete(r, "samples") // The Pi already calculated the summary.
	if stats, ok := r["stats"].(map[string]any); ok && stats["count"] == float64(0) {
		stats["peak"], stats["peakAt"] = nil, nil
	}
	return nil, r, nil
}

type airingArgs struct {
	Hours *int `json:"hours,omitempty" jsonschema:"Look back 24 (default) or 168 hours."`
}

func (d dashboard) airing(ctx context.Context, _ *mcp.CallToolRequest, args airingArgs) (*mcp.CallToolResult, report, error) {
	hours := 24
	if args.Hours != nil {
		hours = *args.Hours
	}
	if hours != 24 && hours != 168 {
		return nil, nil, errors.New("choose 24 or 168 hours")
	}
	var r report
	err := d.get(ctx, "airing", url.Values{"hours": {strconv.Itoa(hours)}}, &r)
	return nil, r, err
}

func tool(name, description string) *mcp.Tool {
	closed := false
	return &mcp.Tool{Name: name, Description: description, Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true, OpenWorldHint: &closed}}
}

func main() {
	address := flag.String("dashboard", "http://air-history.local:8080", "Pi dashboard base URL on your LAN")
	flag.Parse()
	base, err := url.Parse(*address)
	if err != nil || base.Hostname() == "" || (base.Scheme != "http" && base.Scheme != "https") || base.User != nil || base.RawQuery != "" || base.Fragment != "" {
		log.Fatal("provide an http(s) dashboard base URL without credentials, query, or fragment")
	}
	d := dashboard{base, &http.Client{Timeout: 12 * time.Second, Transport: &http.Transport{}, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}
	server := mcp.NewServer(&mcp.Implementation{Name: "bedroom-air", Version: "1.1.0"}, nil)
	mcp.AddTool(server, tool("get_home_status", "Read the bedroom sensor now. The timestamp is the Pi's poll time. A null measurement is unavailable."), d.live)
	mcp.AddTool(server, tool("get_recent_readings", "Read saved one-minute bedroom samples. Times are Unix seconds; CO₂ is ppm, temperature °C, humidity %RH, light lux. Missing samples are gaps."), d.recent)
	mcp.AddTool(server, tool("get_historical_readings", "Get a plot-ready bedroom air curve for an explicit time range of up to 48 hours. Each row includes its interval start (t), archived sample count (n), CO₂ in ppm, temperature in °C, relative humidity in percent, and light in lux. Each point is the mean of available observations in that interval; null means no measurement. Use a 1-minute interval for the most detail."), d.historical)
	mcp.AddTool(server, tool("get_night_report", "Summarize a bedroom night (20:00–08:00 Pi local time). Peak is ppm; above and covered are observed seconds. Times are Unix seconds. Report coverage alongside results."), d.night)
	mcp.AddTool(server, tool("get_airing_events", "List inferred airing events from CO₂ drops, with temperatures in °C and recovery when available. Times are Unix seconds, covered is seconds. No window sensor or energy meter is involved."), d.airing)
	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}
