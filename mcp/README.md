# Ask Codex about your bedroom air

Codex on your Mac can read the same bedroom monitor as Safari. The Pi keeps logging while the Mac is asleep. When you ask a question, Codex starts a local Go program over standard input/output. The program reads the Pi's dashboard over your home network and sends the requested result to the Codex conversation.

## Connect your Mac

Check that Safari on the Mac can open `http://air-history.local:8080/`. From the repository root, with Go and the Codex CLI installed, run

```sh
cd mcp
mkdir -p build
go build -o build/bedroom-air-mcp .
codex mcp add bedroom-air -- "$PWD/build/bedroom-air-mcp"
```

Open a new Codex chat and ask **“What’s the CO₂ in my bedroom right now?”** If you use a different dashboard address, append `-dashboard http://YOUR-PI:8080` to the registration command. The program uses the same network connection to the Pi as Safari. There is no additional network listener. To disconnect it from Codex, run `codex mcp remove bedroom-air`.

| Ask | What the tool reads |
| --- | --- |
| “What are the CO₂, temperature, humidity, and light right now?” | Current values with the Pi's poll time. A missing sensor value is null. An offline sensor or a timestamp more than 30 seconds from the Mac's clock produces an error. |
| “Has CO₂ been rising over the past hour?” | Saved one-minute samples for the last 1–120 minutes. Gaps stay visible. |
| “How long was CO₂ above 1,000 ppm last night?” | The Pi's overnight report, with peak, observed time above the threshold, and total coverage. An empty night has no peak. |
| “Did it look like I aired out the room today?” | Likely airing events over the last 24 hours or seven days, including available temperature and recovery data. The Pi infers events from CO₂ drops. |
