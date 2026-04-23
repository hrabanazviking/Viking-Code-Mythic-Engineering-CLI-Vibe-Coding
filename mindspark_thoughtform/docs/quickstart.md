# Quick Start

Get ThoughtForge running in under 5 minutes.

---

## Prerequisites

- Python 3.10, 3.11, or 3.12
- Git
- 500 MB free disk space (for reference knowledge only)
- A GGUF model file *(optional — knowledge-only mode works without one)*

---

## Installation

=== "Linux"

    ```bash
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    chmod +x scripts/install_linux.sh
    ./scripts/install_linux.sh --profile desktop_cpu
    source .venv/bin/activate
    ```

=== "macOS"

    ```bash
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    chmod +x scripts/install_mac.sh
    ./scripts/install_mac.sh --profile desktop_cpu
    # Apple Silicon: add --metal for Metal GPU acceleration
    source .venv/bin/activate
    ```

=== "Windows"

    ```powershell
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
    .\scripts\install_windows.ps1 -Profile desktop_cpu
    .\.venv\Scripts\Activate.ps1
    ```

=== "Termux (Android)"

    ```bash
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    chmod +x scripts/install_termux.sh
    ./scripts/install_termux.sh --profile phone_low
    source .venv/bin/activate
    ```

=== "Raspberry Pi"

    ```bash
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    chmod +x scripts/install_pi.sh
    ./scripts/install_pi.sh  # auto-detects Pi Zero vs Pi 5
    source .venv/bin/activate
    ```

=== "Docker"

    ```bash
    git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
    cd MindSpark_ThoughtForge
    docker compose up thoughtforge-desktop
    ```

---

## Build the Knowledge Base

ThoughtForge uses an offline SQLite knowledge database. Start with the built-in
reference data (fast — seconds to minutes):

```bash
python forge_memory.py reference
```

For full knowledge (requires Wikidata dump — 100 GB+, many hours):

```bash
python forge_memory.py all
```

Check status:

```bash
python forge_memory.py status
```

---

## Run

### Interactive REPL

```bash
python run_thoughtforge.py
```

```
MindSpark: ThoughtForge
The forge is ready. Type 'exit' or 'quit' to leave.

Forge> What is Yggdrasil?

════════════════════════════════════════════════════════════════════════
Yggdrasil is the immense sacred tree in Norse cosmology, connecting
the nine worlds: Asgard, Midgard, Jotunheim, and six others...
════════════════════════════════════════════════════════════════════════
Citations   : Q42240
Confidence  : 0.712  [good]
Enforcement : PASS
Tokens      : 87
```

### Single Query

```bash
python run_thoughtforge.py "What are the nine worlds?"
```

### With a GGUF Model

```bash
python run_thoughtforge.py --model /models/phi-3-mini-q4.gguf --profile desktop_cpu
```

### Debug Logging

```bash
python run_thoughtforge.py --debug "Who is Loki?"
```

---

## Knowledge-Only Mode

ThoughtForge works without a GGUF model — it assembles a knowledge summary
from retrieved records. Ideal for Pi Zero, low-RAM devices, or testing:

```bash
python run_thoughtforge.py  # no --model flag = knowledge-only mode
```

---

## Building an Edge Subset

For Pi Zero or phone (< 1 GB knowledge DB):

```bash
python - <<'EOF'
from pathlib import Path
from thoughtforge.etl.subset import EdgeSubsetBuilder

builder = EdgeSubsetBuilder()
result = builder.build(
    source_db=Path("data/thoughtforge.db"),
    profile_id="pi_zero",        # 50K entities
)
print(f"Subset: {result.entities_copied} entities → {result.output_path}")
EOF
```

---

## Next Steps

- See [Hardware Profiles](hardware_profiles.md) for profile tuning
- See [API Reference](api.md) for `ThoughtForgeCore` integration
