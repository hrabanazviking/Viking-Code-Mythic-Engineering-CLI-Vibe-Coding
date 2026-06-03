# 🌌 Project Yggdrasil: The Unified Intelligence Protocol

## 1. The Vision: One Tree, One Breath

In this game, the Nine Worlds and the Gods are not isolated scripts; they are limbs of **Yggdrasil**. For the world to feel alive, every interaction—from the Norns weaving fate to the flight of Huginn and Muninn—must be powered by the central "nervous system."

**The Golden Rule:** Every Python script that requires decision-making, dialogue, or world-state updates **must** call the OpenRouter API. There are no "static" NPCs or hard-coded fates.

---

## 2. Technical Mandate: The `config.yaml` Source

To maintain the integrity of the Great Tree, we do not hard-code logic. We use the **OpenRouter API** as our universal oracle.

* **Single Source of Truth:** All scripts must import the API key and model selection from the root `config.yaml`.
* **Constant Flow:** Every action is a signal passed through the "trunk" (the API), processed, and returned to the "branches" (the game world).

### The Web of Connections

| Entity | Role in the Web | AI Dependency |
| --- | --- | --- |
| **The 3 Norns** | Narrative Consistency | Calls API to determine if current actions align with the "Web of Wyrd." |
| **Odin/Freyja** | High-Level Logic | Calls API to provide cryptic guidance based on the player's history. |
| **The 9 Worlds** | Environmental Flux | Calls API to procedurally shift atmosphere and "mood" of the realm. |
| **The 2 Ravens** | Data Fetchers | Use API to summarize player actions and report them to the "Odin" logic block. |

---

## 3. Implementation Workflow

If you are writing a script for a character, an item, or a world event, it must follow this cycle:

1. **Listen:** Gather local game state (Python variables).
2. **Consult:** Send that state to the **OpenRouter API** using the credentials in `config.yaml`.
3. **Act:** Receive the JSON response and translate it into game-world signals.
4. **Propagate:** Pass the resulting data to any other connected scripts (e.g., if a player speaks to Freyja, the Norns must "feel" the ripple).

> **Note:** We are not building a collection of isolated scripts. We are building a **Cosmic Tree Being**. If one script fails to call the API, that branch of the tree dies, and the immersion is broken.

---

## 4. The "Web of Wyrd" Logic

In Python terms, think of the game as a series of observers.

* **Input:** Player Action.
* **Process:** `OpenRouter_Call(prompt, config['api_key'])`
* **Output:** Signal sent to all listeners (Narrator, NPCs, Environment).

Everything is in constant interaction with itself. No script is an island.

---

### How to use this

I recommend saving this as `YGGDRASIL_MANIFESTO.md` in your main project folder.

