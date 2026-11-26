package main

import (
	"context"
	"errors"
	"math"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const historyWindow = 48 * time.Hour // Maximum range supported by the Pi's /api/history.

type historicalArgs struct {
	StartTime string `json:"start_time" jsonschema:"Inclusive RFC 3339 timestamp with timezone offset or Z."`
	EndTime   string `json:"end_time" jsonschema:"Exclusive RFC 3339 timestamp with timezone offset or Z. Up to 48 hours after start_time."`
	Interval  *int   `json:"sampling_interval_minutes,omitempty" jsonschema:"Width of each interval in whole minutes (1–2880). Default 5; use 1 for the native logging cadence."`
}

type historicalPoint struct {
	Time        string   `json:"t" jsonschema:"Inclusive start of this interval in RFC 3339 format."`
	Count       int      `json:"n" jsonschema:"Number of archived rows, including rows with missing sensor values."`
	CO2         *float64 `json:"co2" jsonschema:"Mean carbon dioxide concentration in ppm."`
	Temperature *float64 `json:"temperature" jsonschema:"Mean temperature in degrees Celsius."`
	Humidity    *float64 `json:"humidity" jsonschema:"Mean relative humidity in percent."`
	Lux         *float64 `json:"lux" jsonschema:"Mean illuminance in lux."`
}

type historicalResult struct {
	StartTime string            `json:"start_time"`
	EndTime   string            `json:"end_time" jsonschema:"Exclusive end of the final interval, which may be shorter."`
	Interval  int               `json:"sampling_interval_minutes"`
	Readings  []historicalPoint `json:"readings" jsonschema:"Chronological, timestamped intervals. A null value means that sensor had no measurements."`
}

// Stored timestamps are integer seconds. Both bounds of [start, end) round up.
func ceilUnix(t time.Time) int64 {
	if t.Nanosecond() != 0 {
		return t.Unix() + 1
	}
	return t.Unix()
}

func (d dashboard) historical(ctx context.Context, _ *mcp.CallToolRequest, args historicalArgs) (*mcp.CallToolResult, historicalResult, error) {
	start, startErr := time.Parse(time.RFC3339Nano, args.StartTime)
	end, endErr := time.Parse(time.RFC3339Nano, args.EndTime)
	if startErr != nil || endErr != nil {
		return nil, historicalResult{}, errors.New("provide start_time and end_time as RFC 3339 timestamps with an offset, for example 2026-01-15T20:00:00+09:00")
	}
	span := end.Sub(start)
	if start.Unix() < 0 || span <= 0 || span > historyWindow {
		return nil, historicalResult{}, errors.New("choose a start at or after 1970-01-01 UTC and a later end within 48 hours; split longer requests into adjacent windows")
	}
	minutes := 5
	if args.Interval != nil {
		minutes = *args.Interval
	}
	if minutes < 1 || minutes > int(historyWindow/time.Minute) {
		return nil, historicalResult{}, errors.New("choose a sampling_interval_minutes between 1 and 2880")
	}
	step := time.Duration(minutes) * time.Minute
	n := int((span + step - 1) / step)
	r := historicalResult{
		StartTime: start.Format(time.RFC3339Nano), EndTime: end.Format(time.RFC3339Nano), Interval: minutes,
		Readings: make([]historicalPoint, n),
	}
	from, to := ceilUnix(start), ceilUnix(end)
	var rows []sample
	if from < to {
		var err error
		rows, err = d.savedReadings(ctx, from, to)
		if err != nil {
			return nil, historicalResult{}, err
		}
	}
	for i := range r.Readings {
		// The dashboard delivers rows in ascending timestamp order.
		stop := min(from+int64((i+1)*minutes)*60, to)
		count := 0
		for count < len(rows) && rows[count].Time < stop {
			count++
		}
		bucket := rows[:count]
		r.Readings[i] = historicalPoint{
			Time:        start.Add(time.Duration(i) * step).Format(time.RFC3339Nano),
			Count:       count,
			CO2:         sensorMean(bucket, func(s sample) *int { return s.CO2 }),
			Temperature: sensorMean(bucket, func(s sample) *float64 { return s.Temperature }),
			Humidity:    sensorMean(bucket, func(s sample) *float64 { return s.Humidity }),
			Lux:         sensorMean(bucket, func(s sample) *float64 { return s.Lux }),
		}
		rows = rows[count:]
	}
	return nil, r, nil
}

func sensorMean[T int | float64](rows []sample, value func(sample) *T) *float64 {
	var sum float64
	count := 0
	for _, row := range rows {
		if v := value(row); v != nil {
			sum += float64(*v)
			count++
		}
	}
	if count == 0 {
		return nil
	}
	mean := math.Round(sum/float64(count)*100) / 100
	return &mean
}
