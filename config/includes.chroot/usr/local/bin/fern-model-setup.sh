#!/usr/bin/env bash
# ╭─────────────────────────────────────────────────────────╮
# │  fern-model-setup — FernOS local AI model installer     │
# │  Checks hardware, recommends a model, lets you pick.    │
# ╰─────────────────────────────────────────────────────────╯

set -euo pipefail

# ─── Theme ────────────────────────────────────────────────
TITLE="FernOS — AI Model Setup"
W=480  # default dialog width

# Write a temporary GTK3 CSS file for the fern aesthetic
CSS_FILE=$(mktemp /tmp/fernos-XXXXXX.css)
cat > "$CSS_FILE" <<'CSS'
* {
    font-family: "DM Sans", "Cantarell", sans-serif;
    color: #e8f5e0;
}

window, .background {
    background-color: #0d1a0e;
    border-radius: 12px;
}

.dialog-vbox, GtkVBox, box {
    background-color: transparent;
}

button {
    background: rgba(184, 240, 160, 0.12);
    border: 1px solid rgba(184, 240, 160, 0.45);
    border-radius: 8px;
    color: #b8f0a0;
    padding: 6px 16px;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.85em;
}

button:hover {
    background: rgba(125, 234, 106, 0.22);
    border-color: #7dea6a;
    color: #ffffff;
}

button:active {
    background: rgba(125, 234, 106, 0.35);
}

entry {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: #ffffff;
}

progressbar trough {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    min-height: 8px;
}

progressbar progress {
    background: linear-gradient(to right, #7dea6a, #b8f0a0);
    border-radius: 6px;
}

treeview {
    background-color: rgba(13, 26, 14, 0.7);
    color: #e8f5e0;
    border-radius: 6px;
}

treeview:selected {
    background: rgba(184, 240, 160, 0.2);
    color: #ffffff;
}

label {
    color: #e8f5e0;
}

CSS

export GTK_THEME=""
export GTK3_RC_FILES=""

# Apply CSS via GTK_CSS variable (works in GTK3 yad 0.40)
export GTK_CSS_FILE="$CSS_FILE"

# yad base flags reused everywhere
YAD=(
    yad
    --title="$TITLE"
    --center
    --on-top
    --borders=18
    --width=$W
)

# ─── Helpers ──────────────────────────────────────────────
die() {
    "${YAD[@]}" --error --text="$1" --button="Close:1"
    exit 1
}

confirm() {
    # $1 = text, $2 = ok label, $3 = cancel label
    "${YAD[@]}" --question \
        --text="$1" \
        --button="$3:1" \
        --button="$2:0"
}

# Check dependencies
for cmd in yad awk grep; do
    command -v "$cmd" &>/dev/null || { echo "Missing: $cmd"; exit 1; }
done
#if ! command -v ollama &>/dev/null; then
#    die "<b>ollama</b> is not installed.\n\nPlease ensure FernOS is #fully set up before running this."
#fi

# ─── Step 1: Progress spinner — read system resources ─────
(
    echo "2"  ; echo "# Detecting CPU..."
    sleep 0.4

    CPU_MODEL=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null \
        | awk -F': ' '{print $2}' | sed 's/  */ /g' || echo "Unknown")
    CPU_CORES=$(nproc 2>/dev/null || echo "?")

    echo "20" ; echo "# Reading memory..."
    sleep 0.3

    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    AVAIL_RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))
    AVAIL_RAM_GB=$(( AVAIL_RAM_KB / 1024 / 1024 ))

    echo "40" ; echo "# Checking storage..."
    sleep 0.3

    OLLAMA_DIR="$HOME/.ollama/models"
    mkdir -p "$OLLAMA_DIR"
    FREE_DISK_GB=$(df -BG "$OLLAMA_DIR" | awk 'NR==2 {gsub("G",""); print $4}')

    echo "58" ; echo "# Probing GPU..."
    sleep 0.4

    GPU_INFO="None detected — CPU inference will be used"
    VRAM_GB=0
    if command -v nvidia-smi &>/dev/null; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "")
        VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
        if [[ -n "$GPU_NAME" && "$VRAM_MB" -gt 0 ]]; then
            VRAM_GB=$(( VRAM_MB / 1024 ))
            GPU_INFO="$GPU_NAME  (${VRAM_GB} GB VRAM)"
        fi
    elif command -v rocm-smi &>/dev/null; then
        GPU_INFO=$(rocm-smi --showproductname 2>/dev/null \
            | grep -m1 "Card series" | awk -F': ' '{print $2}' \
            || echo "AMD GPU detected")
    fi

    echo "80" ; echo "# Calculating recommendation..."
    sleep 0.3

    cat > /tmp/fernos_sysinfo.env <<EOF
CPU_MODEL="$CPU_MODEL"
CPU_CORES="$CPU_CORES"
TOTAL_RAM_GB="$TOTAL_RAM_GB"
AVAIL_RAM_GB="$AVAIL_RAM_GB"
FREE_DISK_GB="$FREE_DISK_GB"
OLLAMA_DIR="$OLLAMA_DIR"
GPU_INFO="$GPU_INFO"
VRAM_GB="$VRAM_GB"
EOF

    echo "100" ; echo "# Done."
    sleep 0.2

) | "${YAD[@]}" --progress \
    --text="<span font='DM Mono 10' foreground='#b8f0a0'><b>🌿  FernOS</b></span>\n<span foreground='#a0c890'>Reading your system...</span>" \
    --percentage=0 \
    --auto-close \
    --no-cancel \
    --bar=NORM \
    || die "Setup was cancelled."

# ─── Load sysinfo ─────────────────────────────────────────
# shellcheck source=/dev/null
source /tmp/fernos_sysinfo.env
rm -f /tmp/fernos_sysinfo.env

# ─── Step 2: Recommend a model ────────────────────────────
if   (( VRAM_GB >= 48 )); then REC_MODEL="llama3.1:70b"  ; REC_SIZE="~40 GB" ; REC_NEEDS="48 GB VRAM"
elif (( VRAM_GB >= 24 )); then REC_MODEL="llama3.1:70b"  ; REC_SIZE="~40 GB" ; REC_NEEDS="24 GB VRAM (q4)"
elif (( VRAM_GB >= 16 )); then REC_MODEL="llama3.1:30b"  ; REC_SIZE="~18 GB" ; REC_NEEDS="16 GB VRAM"
elif (( VRAM_GB >=  8 )); then REC_MODEL="llama3.1:8b"   ; REC_SIZE="~5 GB"  ; REC_NEEDS="8 GB VRAM"
elif (( VRAM_GB >=  6 )); then REC_MODEL="llama3.2:3b"   ; REC_SIZE="~2 GB"  ; REC_NEEDS="6 GB VRAM"
elif (( TOTAL_RAM_GB >= 32 )); then REC_MODEL="llama3.1:8b" ; REC_SIZE="~5 GB" ; REC_NEEDS="32 GB RAM (CPU)"
elif (( TOTAL_RAM_GB >= 16 )); then REC_MODEL="llama3.2:3b" ; REC_SIZE="~2 GB" ; REC_NEEDS="16 GB RAM (CPU)"
else                            REC_MODEL="llama3.2:1b"   ; REC_SIZE="~1.3 GB"; REC_NEEDS="any hardware"
fi

# ─── Step 3: System summary + confirm ─────────────────────
SUMMARY="\
<span font='DM Mono 9' foreground='#b8f0a0'>── Your system ─────────────────────────</span>

<span font='DM Mono 9'>  CPU      </span><b>$CPU_MODEL</b>  ($CPU_CORES cores)
<span font='DM Mono 9'>  RAM      </span><b>${TOTAL_RAM_GB} GB</b> total  ·  ${AVAIL_RAM_GB} GB free
<span font='DM Mono 9'>  Disk     </span><b>${FREE_DISK_GB} GB</b> free  →  $OLLAMA_DIR
<span font='DM Mono 9'>  GPU      </span><b>$GPU_INFO</b>

<span font='DM Mono 9' foreground='#b8f0a0'>── Recommended model ───────────────────</span>

<span font='DM Mono 9'>  Model    </span><b>$REC_MODEL</b>
<span font='DM Mono 9'>  Size     </span>$REC_SIZE download
<span font='DM Mono 9'>  Needs    </span>$REC_NEEDS

Does this look good?"

"${YAD[@]}" --question \
    --width=520 \
    --text="$SUMMARY" \
    --button="No, let me choose:1" \
    --button="Yes, pull $REC_MODEL:0" \
    && CHOSEN_MODEL="$REC_MODEL" \
    || CHOSEN_MODEL=""

# ─── Step 4: Model picker ─────────────────────────────────
if [[ -z "$CHOSEN_MODEL" ]]; then

    CHOSEN_MODEL=$("${YAD[@]}" --list \
        --width=620 --height=460 \
        --text="<span font='DM Mono 9' foreground='#b8f0a0'><b>🌿  Choose a model</b></span>\n\nYour system: <b>${TOTAL_RAM_GB} GB RAM</b>  ·  GPU: <b>$GPU_INFO</b>\nRecommended: <b>$REC_MODEL</b>" \
        --column="Model" \
        --column="Size" \
        --column="Needs" \
        --column="Notes" \
        --print-column=1 \
        --no-selection \
        "llama3.2:1b"   "1.3 GB"  "Any hardware"      "Fast, CPU-friendly" \
        "llama3.2:3b"   "2 GB"    "6 GB VRAM / 8 GB"  "Good balance" \
        "llama3.1:8b"   "5 GB"    "8 GB VRAM / 16 GB" "Recommended for most" \
        "llama3.1:13b"  "8 GB"    "16 GB VRAM / 32 GB" "Higher quality" \
        "llama3.1:30b"  "18 GB"   "24 GB VRAM"        "Needs real GPU" \
        "llama3.1:70b"  "40 GB"   "48 GB VRAM"        "Best quality" \
        "mistral:7b"    "4 GB"    "8 GB VRAM / 16 GB" "Great for coding" \
        "codellama:7b"  "4 GB"    "8 GB VRAM / 16 GB" "Code-focused" \
        "phi3:mini"     "2.3 GB"  "6 GB VRAM / 8 GB"  "Fast and efficient" \
        "gemma2:2b"     "1.6 GB"  "Any hardware"      "Google, very fast" \
        --button="Cancel:1" \
        --button="Select:0" \
        2>/dev/null) || die "No model selected."

    # yad --list returns "value|" with a trailing pipe
    CHOSEN_MODEL="${CHOSEN_MODEL%%|*}"
    CHOSEN_MODEL="${CHOSEN_MODEL// /}"
    [[ -z "$CHOSEN_MODEL" ]] && die "No model selected."

fi

# ─── Step 5: Disk space check ─────────────────────────────
declare -A MODEL_SIZES=(
    ["llama3.2:1b"]=2   ["llama3.2:3b"]=3
    ["llama3.1:8b"]=6   ["llama3.1:13b"]=9
    ["llama3.1:30b"]=19 ["llama3.1:70b"]=41
    ["mistral:7b"]=5    ["codellama:7b"]=5
    ["phi3:mini"]=3     ["gemma2:2b"]=2
)
NEEDED_GB="${MODEL_SIZES[$CHOSEN_MODEL]:-10}"

if (( FREE_DISK_GB < NEEDED_GB )); then
    die "Not enough disk space.\n\n<b>$CHOSEN_MODEL</b> needs ~${NEEDED_GB} GB.\nYou have ${FREE_DISK_GB} GB free.\n\nFree up space and try again."
fi

# ─── Step 6: Confirm + pull ───────────────────────────────
"${YAD[@]}" --info \
    --text="<span font='DM Mono 9'>Ready to pull:\n\n  <b>$CHOSEN_MODEL</b>\n  ~${NEEDED_GB} GB download\n\nClick OK to start.</span>" \
    --button="Start download:0" \
    --button="Cancel:1" \
    || exit 0

(
    ollama pull "$CHOSEN_MODEL" 2>&1 | while IFS= read -r line; do
        PCT=$(echo "$line" | grep -oP '\d+(?=%)' | tail -1 || true)
        CLEAN=$(echo "$line" | sed 's/\x1B\[[0-9;]*[mK]//g')
        [[ -n "$PCT" ]] && echo "$PCT" || echo "0"
        echo "# $CLEAN"
    done
) | "${YAD[@]}" --progress \
    --text="<span font='DM Mono 9' foreground='#b8f0a0'><b>🌿  Pulling $CHOSEN_MODEL</b></span>\n<span foreground='#a0c890'>This window will close when the download is complete.</span>" \
    --percentage=0 \
    --auto-close \
    --no-cancel \
    --bar=NORM \
    || die "Pull failed or was interrupted.\n\nRetry manually:\n\n  <span font='DM Mono 9'>ollama pull $CHOSEN_MODEL</span>"

# ─── Step 7: Done ─────────────────────────────────────────
"${YAD[@]}" --info \
    --text="<span font='DM Mono 9' foreground='#b8f0a0'>✓  Model ready</span>\n\n<b>$CHOSEN_MODEL</b> is installed and available.\n\nRun it in the terminal:\n\n<span font='DM Mono 9'>  ollama run $CHOSEN_MODEL</span>\n\nOr open <b>Fern AI Chat</b> from the app menu." \
    --button="Done:0"

rm -f "$CSS_FILE"
exit 0
