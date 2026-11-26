package main

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/brutella/hap"
	"github.com/brutella/hap/accessory"
	"github.com/brutella/hap/characteristic"
	"github.com/brutella/hap/service"
)

// Create the pairing code once. The state directory is private to this service.
func pairingPIN(dir string) (string, error) {
	path := filepath.Join(dir, "setup-pin")
	data, err := os.ReadFile(path)
	if err == nil {
		return strings.TrimSpace(string(data)), nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return "", err
	}
	for {
		n, err := rand.Int(rand.Reader, big.NewInt(100000000))
		if err != nil {
			return "", err
		}
		pin := fmt.Sprintf("%08d", n.Int64())
		if hap.InvalidPins[pin] {
			continue
		}
		temp, err := os.CreateTemp(dir, ".pin-")
		if err != nil {
			return "", err
		}
		defer os.Remove(temp.Name())
		_, err = temp.WriteString(pin + "\n")
		if err == nil {
			err = temp.Sync()
		}
		closeErr := temp.Close()
		if err != nil {
			return "", err
		}
		if closeErr != nil {
			return "", closeErr
		}
		if err = os.Link(temp.Name(), path); errors.Is(err, os.ErrExist) {
			return pairingPIN(dir)
		}
		return pin, err
	}
}

// Faulted sensors retain the last measured value internally. A Home request for
// one receives the HAP communication-error status until a new reading arrives.
func addSensor(a *accessory.A, s *service.S, name string, values ...*characteristic.C) *characteristic.StatusFault {
	label := characteristic.NewName()
	label.SetValue(name)
	s.AddC(label.C)
	fault := characteristic.NewStatusFault()
	fault.SetValue(characteristic.StatusFaultGeneralFault)
	s.AddC(fault.C)
	for _, c := range values {
		c.ValueRequestFunc = func(*http.Request) (any, int) {
			if fault.Value() != characteristic.StatusFaultNoFault {
				return nil, -70402
			}
			return c.Value(), 0
		}
	}
	a.AddS(s)
	return fault
}

func serveHome(ctx context.Context, dir, liveURL string) error {
	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}
	pin, err := pairingPIN(dir)
	if err != nil {
		return err
	}
	a := accessory.New(accessory.Info{Name: "Bedroom Air", Manufacturer: "DIY", Model: "ESP32 Room Monitor", SerialNumber: "BEDROOM-AIR-01", Firmware: "1.0.0"}, accessory.TypeSensor)
	co2 := service.NewCarbonDioxideSensor()
	co2.Primary = true
	level := characteristic.NewCarbonDioxideLevel()
	level.Unit = characteristic.UnitPPM
	co2.AddC(level.C)
	co2Fault := addSensor(a, co2.S, "Bedroom CO₂", co2.CarbonDioxideDetected.C, level.C)
	temp := service.NewTemperatureSensor()
	temp.CurrentTemperature.SetMinValue(-40)
	tempFault := addSensor(a, temp.S, "Bedroom Temperature", temp.CurrentTemperature.C)
	hum := service.NewHumiditySensor()
	humFault := addSensor(a, hum.S, "Bedroom Humidity", hum.CurrentRelativeHumidity.C)
	server, err := hap.NewServer(hap.NewFsStore(dir), a)
	if err != nil {
		return err
	}
	server.Pin = pin
	server.SetupId = "BAIR"
	server.Addr = ":51826"
	client := &http.Client{Timeout: 10 * time.Second}
	defer client.CloseIdleConnections()
	update := func() {
		r, err := fetch(ctx, client, liveURL)
		if err != nil {
			r = reading{}
		}
		if r.CO2 == nil {
			co2Fault.SetValue(1)
		} else {
			level.SetValue(float64(*r.CO2))
			detected := characteristic.CarbonDioxideDetectedCO2LevelsNormal
			if *r.CO2 >= 1500 {
				detected = characteristic.CarbonDioxideDetectedCO2LevelsAbnormal
			}
			co2.CarbonDioxideDetected.SetValue(detected)
			co2Fault.SetValue(0)
		}
		updateFloat := func(value *float64, c *characteristic.Float, fault *characteristic.StatusFault) {
			if value == nil {
				fault.SetValue(1)
				return
			}
			c.SetValue(*value)
			fault.SetValue(0)
		}
		updateFloat(r.Temperature, temp.CurrentTemperature.Float, tempFault)
		updateFloat(r.Humidity, hum.CurrentRelativeHumidity.Float, humFault)
	}
	update()
	go func() {
		ticker := time.NewTicker(15 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				update()
			}
		}
	}()
	return server.ListenAndServe(ctx)
}
