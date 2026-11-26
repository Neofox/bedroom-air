package main

import (
	"context"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

var errNoBuffer = errors.New("firmware has no minute buffer")

type minutePage struct {
	Boot    string `json:"boot"`
	Uptime  int64  `json:"uptime"`
	Latest  int64  `json:"latest"`
	Samples []struct {
		reading
		Seq int64 `json:"seq"`
		Up  int64 `json:"up"`
	} `json:"samples"`
}

// The clock anchor and the cursor are committed with the samples. Replaying a
// page after a timeout or a Pi restart therefore preserves its timestamps.
type bufferCursor struct {
	boot                  string
	seq, epoch, legacyEnd int64
}

func syncBuffer(ctx context.Context, db *sql.DB, source *sensor) error {
	var c bufferCursor
	err := db.QueryRowContext(ctx, "SELECT boot,seq,epoch,legacy_end FROM buffer_cursor WHERE id=1").Scan(&c.boot, &c.seq, &c.epoch, &c.legacyEnd)
	if errors.Is(err, sql.ErrNoRows) {
		err = db.QueryRowContext(ctx, "SELECT coalesce(max(t),0) FROM readings").Scan(&c.legacyEnd)
	}
	if err != nil {
		return err
	}
	endpoint, err := url.Parse(source.url)
	if err != nil {
		return err
	}
	endpoint.Path = "/api/minutes"
	for {
		endpoint.RawQuery = url.Values{"boot": {c.boot}, "after": {strconv.FormatInt(c.seq, 10)}}.Encode()
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
		if err != nil {
			return err
		}
		res, err := source.client.Do(req)
		if err != nil {
			return err
		}
		received := time.Now().Unix()
		var p minutePage
		if res.StatusCode == http.StatusOK {
			err = json.NewDecoder(io.LimitReader(res.Body, 32*1024)).Decode(&p)
		} else if res.StatusCode == http.StatusNotFound {
			err = errNoBuffer
		} else {
			err = fmt.Errorf("buffer returned %s", res.Status)
		}
		res.Body.Close()
		if err != nil {
			return err
		}
		if err := savePage(ctx, db, &c, p, received); err != nil {
			return err
		}
		if c.seq >= p.Latest {
			return nil
		}
	}
}

func savePage(ctx context.Context, db *sql.DB, c *bufferCursor, p minutePage, received int64) error {
	if _, err := hex.DecodeString(p.Boot); err != nil || len(p.Boot) != 16 || p.Uptime < 0 || p.Latest < 0 || len(p.Samples) > 48 {
		return errors.New("invalid minute buffer response")
	}
	next := *c
	if p.Boot != next.boot {
		next.boot, next.seq, next.epoch = p.Boot, 0, received-p.Uptime
	}
	if len(p.Samples) == 0 {
		if next.seq != p.Latest {
			return errors.New("incomplete minute buffer response")
		}
		*c = next
		return nil
	}
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for _, s := range p.Samples {
		if s.Seq <= next.seq || s.Seq > p.Latest || s.Up < 0 || s.Up > p.Uptime {
			return errors.New("invalid minute sample")
		}
		t := next.epoch + s.Up
		// On the first upgrade the old logger may already have polled this
		// minute. Keep its timestamp and fill only its missing measurements.
		if t <= next.legacyEnd+29 {
			var old int64
			err = tx.QueryRowContext(ctx, "SELECT t FROM readings WHERE t BETWEEN ? AND ? AND t<=? ORDER BY abs(t-?) LIMIT 1", t-29, t+29, next.legacyEnd, t).Scan(&old)
			if err == nil {
				t = old
			} else if !errors.Is(err, sql.ErrNoRows) {
				return err
			}
		}
		_, err = tx.ExecContext(ctx, `INSERT INTO readings(t,co2,temperature,humidity,lux) VALUES(?,?,?,?,?)
			ON CONFLICT(t) DO UPDATE SET co2=coalesce(readings.co2,excluded.co2),
			temperature=coalesce(readings.temperature,excluded.temperature),
			humidity=coalesce(readings.humidity,excluded.humidity),lux=coalesce(readings.lux,excluded.lux)`,
			t, s.CO2, s.Temperature, s.Humidity, s.Lux)
		if err != nil {
			return err
		}
		next.seq = s.Seq
	}
	if _, err = tx.ExecContext(ctx, "INSERT OR REPLACE INTO buffer_cursor(id,boot,seq,epoch,legacy_end) VALUES(1,?,?,?,?)", next.boot, next.seq, next.epoch, next.legacyEnd); err != nil {
		return err
	}
	if err = tx.Commit(); err != nil {
		return err
	}
	*c = next
	return nil
}
