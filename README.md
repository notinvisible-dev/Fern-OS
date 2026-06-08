# FernOS

> A Linux distro built on Debian 13, with local AI models running entirely on your hardware. No cloud. No subscriptions. Just your machine, doing the work.

FernOS is a Debian 13 (Trixie)-based Linux distribution with a rainforest-inspired frosted glass desktop and deep local AI integration via Ollama. Models from 1B to 70B parameters run directly on your hardware — nothing leaves the machine.

---

## What it is

Most Linux distros that ship with AI features offload the work to a server somewhere. FernOS doesn't. The AI assistant runs locally using Ollama, which means it works offline, has no rate limits, and doesn't require an account or API key. You pick the model, it runs on your CPU or GPU.

The desktop is built around a rainforest aesthetic — frosted glass panels, muted greens, clean typography — without being loud about it. It's designed to look good and get out of the way.

The base is stock Debian 13 stable, so everything under the hood is familiar. Full `apt` support, standard Debian tooling, nothing unusual in the package ecosystem.

---

## Features

**Local AI, built in** — Ollama is installed and configured out of the box. Supported model sizes range from 1B (fast, low RAM) to 70B (high quality, needs serious hardware). The AI assistant is available system-wide, not just in a standalone app.

**Rainforest-themed UI** — Frosted glass panels throughout, muted green palette, custom icon set. Built on top of a lightweight compositor that supports blur and transparency without needing a high-end GPU.

**Debian 13 (Trixie) core** — Inherits Debian's stability and the full `apt`/`dpkg` ecosystem. No custom package manager, no weird repos required.

**Fern-native applications** — A file manager, terminal emulator, and browser skin written specifically for FernOS. These aren't reskins of GNOME or KDE apps; they're built to match the system's look and behaviour end to end.

**Lightweight base** — The default install is small. Background services are minimal. Boot times are short. The assumption is that if you're running a 70B model, you need those resources for the model, not the OS.

**No telemetry** — Nothing is sent home. No crash reports, no usage pings, no opt-out dark patterns anywhere in the stack. The local AI model means that data doesn't leave the machine either.

---

## Bundled applications

| App | Description |
|---|---|
| Terminal | FernOS custom terminal emulator |
| File Manager | Native file browser with glass UI |
| AI Chat | Local model chat interface (Ollama frontend) |
| Browser | Chromium with FernOS skin applied |
| Settings | System configuration panel |
| Text Editor | Lightweight editor, syntax highlighting |
| Image Viewer | Minimal, keyboard-driven |
| Media Player | Audio and video playback |
| Archive Manager | GUI for zip, tar, gz, zst |
| Calendar | Basic calendar, no cloud sync required |

---

## System requirements

Local inference is the main reason these specs are higher than a typical Debian install.

| Component | Minimum | Recommended |
|---|---|---|
| CPU | x86-64, 4 cores | 8+ cores |
| RAM | 16 GB | 32–64 GB (for 30B–70B models) |
| Storage | 50 GB (OS) | 50 GB + 10–40 GB per model |
| GPU | Any (CPU fallback) | NVIDIA with 8 GB+ VRAM |
| Internet | Not required to run | Needed for initial model downloads |
| Architecture | amd64 | amd64 · arm64 |

### Model RAM requirements (rough guide)

| Model size | Minimum RAM | Notes |
|---|---|---|
| 1B–3B | 4–6 GB | Runs well on most hardware, CPU is fine |
| 7B | 8–12 GB | Comfortable with 16 GB RAM |
| 13B | 16 GB | GPU recommended |
| 30B | 32 GB | Needs decent GPU or high RAM |
| 70B | 48–64 GB | Requires high-end GPU or multi-GPU |

CPU inference works on any hardware but is significantly slower for larger models. A dedicated GPU is the practical requirement for 13B and above at usable speeds.

---

## Getting started

> FernOS is currently in early access. ISO downloads are not yet public.

Join the waitlist at [fernos.dev](https://fernos.dev) to be notified when builds are available.

Once released, installation will follow the standard Debian installer flow:

```bash
# Write the ISO to a USB drive
dd if=fernos-1.0-amd64.iso of=/dev/sdX bs=4M status=progress

# Boot from USB and follow the installer
```

After installation, the setup wizard will walk through:
- Display and GPU configuration
- Downloading an initial AI model (or skipping for offline use)
- User preferences for the desktop

---

## AI setup

FernOS ships with [Ollama](https://ollama.com) pre-installed. To pull a model manually after installation:

```bash
# Small and fast (1B)
ollama pull llama3.2:1b

# Good balance (7B)
ollama pull llama3.1:7b

# Large, needs real hardware (70B)
ollama pull llama3.1:70b
```

The system AI assistant automatically uses whichever model is currently active. You can switch models from the Settings panel or via the terminal:

```bash
ollama run llama3.1:8b
```

Models are stored in `~/.ollama/models`. You can move this to a secondary drive if your OS disk is limited.

---

## Repository structure

```
fernos/
├── iso/                  # ISO build scripts and configs
├── packages/             # FernOS-specific packages
│   ├── fern-terminal/    # Custom terminal emulator
│   ├── fern-files/       # File manager
│   ├── fern-chat/        # AI chat frontend (Ollama)
│   └── fern-shell/       # Shell theme and config
├── desktop/              # Compositor config, themes, icons
├── installer/            # Calamares installer customisation
├── docs/                 # Extended documentation
└── website/              # Landing page (fernos.html)
    └── fernos.html
```

---

## Website

The `website/` directory contains `fernos.html` — a single-file static landing page for the waitlist. It uses:

- Vanilla HTML, CSS, and JavaScript — no build step
- [Lucide](https://lucide.dev) icons via CDN
- DM Sans and DM Mono from Google Fonts
- A frosted glass visual style matching the desktop UI

To run it locally, just open the file in a browser. No server required.

---

## Design reference

The desktop aesthetic uses these values throughout. Custom app developers building for FernOS should follow these to stay consistent.

```css
--glass-bg:     rgba(220, 240, 210, 0.18)
--glass-border: rgba(255, 255, 255, 0.3)
--glass-blur:   blur(18px) saturate(1.4)
--accent:       #b8f0a0
--glow:         #7dea6a
--text-primary: #ffffff
--text-muted:   rgba(255, 255, 255, 0.7)
--radius:       14px
```

Fonts: **DM Sans** (UI, headings) and **DM Mono** (labels, code, terminal).

---

## Contributing

FernOS is in early development. Contributions aren't open yet, but that will change once the first public build is out. Watch this repo to get notified.

If you've found a bug in the website or have feedback on the design direction, open an issue.

---

## Contact

Email: [hello@fernos.dev](mailto:hello@fernos.dev)

---

## License

FernOS is built on Debian and inherits the licensing of its upstream components. FernOS-specific code (native apps, desktop configuration, installer customisation) is released under the [GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).

Ollama is developed by [Ollama, Inc.](https://ollama.com) and is not affiliated with FernOS.

---

*FernOS © 2026 — Built on Debian 13*
