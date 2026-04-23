This is the "Great Refactor." By moving to this architecture, you are essentially creating a **Standardized Interface** (the Trunk) and **Modular Plugins** (the Leaves).

When you give this guide to Roo or any AI, it provides them with a rigid blueprint that prevents "hallucination" and path errors. It forces the AI to stop acting like a confused architect and start acting like a builder following a master plan.

---

# 📜 THE YGGDRASIL ARCHITECTURE MANIFESTO

**Directive:** Rebuild the Game Engine for Modular Autonomy and Centralized Intelligence.

## 1. The Core Philosophy: "The Trunk and the Leaves"

The game shall no longer exist as a collection of scripts with redundant logic. It is now a **Centralized Service Model**.

* **The Trunk (`yggdrasil_core.py`):** This is the only file that knows about the "Real World" (file paths, API keys, `config.yaml`, and internet connections).
* **The Leaves (NPCs, Worlds, Narrator):** These files are "World-Blind." They do not know about folders or APIs. They only know how to send and receive signals through the Trunk.

---

## 2. Technical Implementation: The Singleton Orchestrator

Every AI task must begin by ensuring `yggdrasil_core.py` exists in the root. This script manages the **Global State**.

### A. The Orchestrator Logic

The AI must implement the following class structure. This ensures that no matter where a script is moved, it can find its way back to the heart of the tree.

```python
import os
import yaml
import requests
from pathlib import Path

class Yggdrasil:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Yggdrasil, cls).__new__(cls)
            # Find the root: The folder where this core file lives
            cls._instance.root = Path(__file__).resolve().parent
            cls._instance.config = cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = self.root / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"FATAL: config.yaml missing at {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def call_oracle(self, prompt, system_msg="You are a Norse entity.", model=None):
        """Unified OpenRouter API Access."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        key = self.config.get("OPENROUTER_API_KEY")
        model = model or self.config.get("DEFAULT_MODEL", "openai/gpt-3.5-turbo")

        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "http://localhost", # Required by OpenRouter
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        return response.json()['choices'][0]['message']['content']

# The Global Instance
tree = Yggdrasil()

```

---

## 3. The Rules of Engagement for AI Coders

When modifying or creating any game file (e.g., `norns.py`, `freyja.py`, `world_engine.py`), the AI **must** follow these three iron rules:

### Rule 1: No Direct I/O

The script is forbidden from using `open('config.yaml')` or `os.environ`. If it needs data from the config, it must ask the tree:

* **Wrong:** `api_key = os.getenv("KEY")`
* **Right:** `api_key = tree.config.get("KEY")`

### Rule 2: Absolute Path Blindness

The script must never assume where it is. It should use relative imports.

* **Mandatory Header:** Every modular script must start with:
```python
from yggdrasil_core import tree

```



### Rule 3: Functional Isolation

Each file should be a "Plugin." If I move `huginn.py` from the root into a folder called `/ravens/`, it should still function perfectly because it only depends on the `tree` object imported from the core.

---

## 4. How to Fix the Current "Broken" State

The AI's first task is to perform a **Scan and Bind**:

1. **Identify the Core:** Locate the true `config.yaml`.
2. **Establish the Trunk:** Create/Update `yggdrasil_core.py` in that same folder.
3. **Sever the Ghost Roots:** Scan all other `.py` files. Remove any hardcoded strings that look like `../../../...`.
4. **Rewire:** Replace all API calling logic in individual scripts with a single call to `tree.call_oracle()`.

---

## 5. Benefits for the "Modern Viking" Developer

* **Portability:** You can copy the `NorseSagaEngine` folder to a USB drive, a Linux server, or a VR headset, and it will run immediately.
* **AI Safety:** If Roo "thinks" for 160 seconds, it’s because it’s looking for a path. By giving it this guide, you tell it: "The path is always `tree`. Stop looking."
* **ADHD-Friendly:** You only have **one** file to check if the AI connection fails (`yggdrasil_core.py`). You don't have to hunt through 20 files to find which one has the wrong API key.

---

### Next Step for you:

I recommend you **create a new, empty file** in your root called `INSTRUCTIONS_FOR_AI.md` and paste the content above into it. Then, tell Roo:

> "Read `INSTRUCTIONS_FOR_AI.md`. Your mission is to refactor the current broken scripts to match this 'Trunk and Leaf' architecture. Start with `yggdrasil_core.py`."

---

Exactly. In the old way, your game was a collection of sticks piled together. In the **Yggdrasil Architecture**, it becomes a living organism. When you touch a leaf, the trunk feels the vibration.

This "Multi-Dimensional" approach means that the **dimension of the code** (the logic) is finally separated from the **dimension of the physical machine** (the folders and paths).

Here is the final, deep-dive guide for your AI. This is designed to be the "Master Scroll" you give to Roo or any other agent to force them into this new way of being.

---

# 🌌 THE MULTI-DIMENSIONAL REFACTOR: PROJECT YGGDRASIL

**Status:** Critical System Overhaul
**Goal:** Total decoupling of Game Logic from File System Paths.

## 1. The Divine Order (The Architecture)

To reflect the nature of the World Tree, the game is now divided into two planes of existence:

### A. The Root Realm (Infrastructure)

* **File:** `yggdrasil_core.py`
* **Responsibility:** This is the *only* script allowed to know about the physical world. It handles the `config.yaml`, the OpenRouter API credentials, and the physical directory location on the hard drive.
* **Constraint:** It provides the `tree` object to all other scripts.

### B. The Nine Realms (Modular Logic)

* **Files:** `odin.py`, `norns.py`, `freyja.py`, `narrator.py`, etc.
* **Responsibility:** These are pure "vibe" and logic files. They are **Path-Blind**.
* **Constraint:** They are **FORBIDDEN** from importing `os`, `pathlib`, `yaml`, or `json` for the purpose of finding configuration. They must use the `tree` object for all cosmic needs.

---

## 2. Refactoring Instructions for the AI

When refactoring, you must treat every individual `.py` file as a modular branch that can be snapped off and moved anywhere without breaking the tree.

### Step 1: Establish the Trunk (`yggdrasil_core.py`)

Ensure the `Yggdrasil` class is a **Singleton**. It must calculate the `BASE_DIR` once and use that to anchor everything.

```python
# yggdrasil_core.py excerpt
self.base_path = Path(__file__).resolve().parent
self.config_path = self.base_path / "config.yaml"

```

### Step 2: Implement the "Universal Oracle" Call

Every character interaction must go through a single method: `tree.call_oracle()`. This method handles:

1. Fetching the API key from the "Root Realm."
2. Selecting the correct OpenRouter model.
3. Managing the "Web of Wyrd" (passing state between calls).

### Step 3: Purge Hardcoded Path Hallucinations

The AI must scan all scripts and delete any string that looks like:

* `../../../...`
* `..\..\TEMP\...`
* `os.path.join(os.path.dirname(__file__), '..', 'config.yaml')`

**Replace them with:** `tree.base_path / "filename"`

---

## 3. Why This Fixes the "165-Second Thinking" Loop

The AI gets stuck in long thinking loops because it is trying to solve a **Spatial Puzzle** (where is the file?) while solving a **Logic Puzzle** (what does Odin say?).
By providing this guide, you remove the Spatial Puzzle entirely. You are telling the AI: **"The space is solved. Focus only on the logic."**

---

## 4. The "Web of Wyrd" Signal System

For the Nine Realms to communicate "no matter where they are," the `yggdrasil_core.py` should act as a **Signal Relay**.

* If `odin.py` changes the world state, it calls `tree.update_wyrd("ragnarok_level", 5)`.
* If `norns.py` needs to check that state, it calls `tree.get_wyrd("ragnarok_level")`.

No files are exchanged between the two. Only signals through the Tree.

---

### 🛠️ Execution Order for Roo/AI:

1. **Create** `yggdrasil_core.py` based on the Singleton pattern provided.
2. **Verify** it can read `config.yaml` using the dynamic path.
3. **Refactor** `odin.py` to use `from yggdrasil_core import tree`.
4. **Test** the connection.
5. **Repeat** for all other entities.

---

### A Final Note for the Modern Viking

Since you’re dealing with ADHD and Anxiety, this system is your **Shield-Wall**.

* If something breaks, you only have **one** place to look: `yggdrasil_core.py`.
* If the AI makes a mess, it can't "infect" your other files because they are modular and protected by the Trunk.

---

This prompt is designed to be a "Commandment" for Roo. It uses precise technical language to override its tendency to overthink and forces it to adopt the **Yggdrasil Architecture**.

Copy and paste the block below into your Roo/Cline chat.

---

### ⚡ CRITICAL REFACTOR: THE YGGDRASIL TRUNK PROTOCOL

**THE PROBLEM:** The project is currently broken due to hardcoded absolute paths and fragmented AI calling logic. You are hallucinating directory structures outside the project root, creating "ghost files," and breaking the connection between the game scripts and the OpenRouter API.

**THE MISSION:** You must refactor the entire game into a **"Trunk and Leaf"** (Service-Oriented) architecture. This is a multi-dimensional approach where logic is separated from the physical file system.

**STEP 1: INITIALIZE THE TRUNK (`yggdrasil_core.py`)**
Create or update `yggdrasil_core.py` in the root folder. It must:

1. Use a **Singleton Pattern** to ensure only one "Tree" exists.
2. Use `Path(__file__).resolve().parent` to find the root. **Never use absolute strings.**
3. Load `config.yaml` once and store it.
4. Provide a single method `call_oracle(prompt, system_msg)` that handles all OpenRouter API requests.
5. Provide a `state` dictionary to act as the "Web of Wyrd" for cross-script data exchange.

**STEP 2: REWIRE THE LEAVES (MODULAR SCRIPTS)**
Refactor every other script (Odin, Freyja, Norns, Narrator, etc.) as follows:

1. **STRIP** all imports of `os`, `yaml`, `json`, and `requests` related to configuration or API calls.
2. **ADD** `from yggdrasil_core import tree` at the top of every file.
3. **REPLACE** all local API calling logic with `tree.call_oracle()`.
4. **REPLACE** all file-saving/loading with calls to `tree.state`.

**STEP 3: ENFORCE THE BOUNDARY**

* **DO NOT** look at or write to any directory above the folder containing `yggdrasil_core.py`.
* **DO NOT** use `..` in any path.
* **IF** you need to find a file, ask the `tree.root` path object.

**GOAL:** I must be able to move the entire `NorseSagaEngine` folder to any location on any machine, and it must run perfectly without changing a single line of code.

**Respond with "The Tree is Seeded" once you have analyzed the current files and are ready to create `yggdrasil_core.py`.**

---

### Why this works for you:

By using the word **"Singleton"** and **"Service-Oriented,"** you are speaking the AI's native tongue. This stops it from "thinking" for 160 seconds because it now has a specific coding pattern to follow rather than trying to guess your intentions.

Once Roo finishes this, your files will be so modular that you can literally open `odin.py` in a separate window, tell a different AI "Make Odin more aggressive," and it won't matter that the other AI doesn't see your API keys—the code will just work because it's "plugged into the Tree."

**Would you like me to stay on standby while you run this, in case Roo gets confused by your specific `config.yaml` format?**
