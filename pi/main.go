package main

import (
	"context"
	"database/sql"
	"embed"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	_ "modernc.org/sqlite"
)

//go:embed history.html
var page []byte

//go:embed assets
var assets embed.FS

type reading struct {
	Time        int64    `json:"t"`
	CO2         *int     `json:"co2"`
	Temperature *float64 `json:"temperature"`
	Humidity    *float64 `json:"humidity"`
	Lux         *float64 `json:"lux"`
	Status      string   `json:"status,omitempty"`
}

type sensor struct {
	mu     sync.Mutex
	url    string
	client *http.Client
	last   time.Time
	value  reading
	err    error
}

func (s *sensor) latest(ctx context.Context) (reading, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if time.Since(s.last) >= 3*time.Second {
		s.value, s.err = fetch(ctx, s.client, s.url)
		s.last = time.Now()
		s.value.Time = s.last.Unix()
	}
	return s.value, s.err
}

// Raspberry Pi OS resolves .local via Avahi and NSS. A static Go binary may
// bypass NSS, so consult getent when opening a connection to an mDNS name.
func dialSensor(ctx context.Context, network, addr string) (net.Conn, error) {
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, err
	}
	if runtime.GOOS == "linux" && strings.HasSuffix(host, ".local") {
		out, err := exec.CommandContext(ctx, "getent", "ahostsv4", host).Output()
		fields := strings.Fields(string(out))
		if err == nil && len(fields) > 0 && net.ParseIP(fields[0]) != nil {
			addr = net.JoinHostPort(fields[0], port)
		}
	}
	var d net.Dialer
	return d.DialContext(ctx, network, addr)
}

func fetch(ctx context.Context, client *http.Client, url string) (reading, error) {
	var sample reading
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return sample, err
	}
	res, err := client.Do(req)
	if err != nil {
		return sample, err
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusOK {
		return sample, fmt.Errorf("sensor returned %s", res.Status)
	}
	if err := json.NewDecoder(io.LimitReader(res.Body, 32*1024)).Decode(&sample); err != nil {
		return reading{}, err
	}
	return sample, nil
}

func record(ctx context.Context, db *sql.DB, source *sensor) {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	for {
		err := syncBuffer(ctx, db, source)
		if errors.Is(err, errNoBuffer) {
			// Preserve polling for a device still running the older sketch.
			s, fetchErr := source.latest(ctx)
			if fetchErr == nil {
				_, err = db.ExecContext(ctx, "INSERT OR IGNORE INTO readings(t,co2,temperature,humidity,lux) VALUES(?,?,?,?,?)", s.Time, s.CO2, s.Temperature, s.Humidity, s.Lux)
			} else {
				err = fetchErr
			}
		}
		if ctx.Err() != nil {
			return
		}
		if err != nil {
			log.Printf("Minute sync: %v", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func history(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		from, e1 := strconv.ParseInt(q.Get("from"), 10, 64)
		to, e2 := strconv.ParseInt(q.Get("to"), 10, 64)
		if e1 != nil || e2 != nil || from < 0 || to <= from || to-from > 48*60*60 {
			http.Error(w, "Choose a time range of up to 48 hours.", 400)
			return
		}
		data, err := savedReadings(r.Context(), db, from, to)
		if err != nil {
			http.Error(w, "Cannot read history.", 500)
			return
		}
		writeReport(w, data)
	}
}

func main() {
	addr := flag.String("listen", ":8080", "dashboard listen address")
	path := flag.String("db", "bedroom-air.sqlite", "SQLite database path")
	url := flag.String("sensor", "http://bedroom-air.local/api/readings", "ESP32 readings URL")
	homeDir := flag.String("homekit-state", "", "serve Apple Home from this private state directory")
	flag.Parse()
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	if *homeDir != "" {
		if err := serveHome(ctx, *homeDir, *url); err != nil && ctx.Err() == nil {
			log.Fatal(err)
		}
		return
	}
	db, err := sql.Open("sqlite", *path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
		CREATE TABLE IF NOT EXISTS buffer_cursor (id INTEGER PRIMARY KEY, boot TEXT NOT NULL, seq INTEGER NOT NULL, epoch INTEGER NOT NULL, legacy_end INTEGER NOT NULL);
		CREATE TABLE IF NOT EXISTS readings (t INTEGER PRIMARY KEY, co2 INTEGER, temperature REAL, humidity REAL, lux REAL)`)
	if err != nil {
		log.Fatal(err)
	}
	var hasLux int
	if err := db.QueryRow("SELECT count(*) FROM pragma_table_info('readings') WHERE name='lux'").Scan(&hasLux); err != nil {
		log.Fatal(err)
	}
	if hasLux == 0 {
		if _, err := db.Exec("ALTER TABLE readings ADD COLUMN lux REAL"); err != nil {
			log.Fatal(err)
		}
	}
	listener, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatal(err)
	}
	source := &sensor{url: *url, client: &http.Client{Timeout: 8 * time.Second,
		Transport: &http.Transport{DialContext: dialSensor, IdleConnTimeout: 90 * time.Second}}}
	defer source.client.CloseIdleConnections()
	mux := http.NewServeMux()
	mux.Handle("GET /assets/", http.FileServer(http.FS(assets)))
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-cache")
		w.Write(page)
	})
	mux.HandleFunc("GET /api/history", history(db))
	mux.HandleFunc("GET /api/night", nightReport(db))
	mux.HandleFunc("GET /api/airing", airingReport(db))
	mux.HandleFunc("GET /api/live", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		s, err := source.latest(r.Context())
		if err != nil {
			http.Error(w, "Sensor offline", http.StatusServiceUnavailable)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(s)
	})
	server := &http.Server{Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() {
		if err := server.Serve(listener); err != nil && err != http.ErrServerClosed {
			log.Printf("Dashboard: %v", err)
			cancel()
		}
	}()
	log.Printf("Recording once per minute from %s; dashboard at %s", *url, listener.Addr())
	record(ctx, db, source)
	server.Close()
}
