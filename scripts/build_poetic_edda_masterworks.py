from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class LaySpec:
    title: str
    translation_title: str
    motifs: tuple[str, str, str]


LAY_SPECS: tuple[LaySpec, ...] = (
    LaySpec("Völuspá", "The Prophecy of the Seeress", ("Yggdrasil", "Ragnarok", "wyrd")),
    LaySpec("Hávamál", "The Sayings of the High One", ("wisdom", "guest-right", "doom")),
    LaySpec("Vafþrúðnismál", "The Lay of Vafthrudnir", ("riddle", "giant-lore", "fate")),
    LaySpec("Grímnismál", "The Lay of Grimnir", ("hall-names", "worlds", "Odin")),
    LaySpec("Skírnismál", "The Lay of Skirnir", ("wooing", "threat-spell", "Gerdr")),
    LaySpec("Hárbarðsljóð", "The Lay of Harbarth", ("flyting", "ferry", "boast")),
    LaySpec("Hymiskviða", "The Lay of Hymir", ("ale-kettle", "whale-road", "Jormungand")),
    LaySpec("Lokasenna", "The Flyting of Loki", ("feast-hall", "leasings", "insult")),
    LaySpec("Þrymskviða", "The Lay of Thrym", ("hammer", "bride-guise", "giant-hall")),
    LaySpec("Völundarkviða", "The Lay of Volund", ("smith", "wing-cloak", "vengeance")),
    LaySpec("Alvíssmál", "The Lay of Alvis", ("dwarf", "name-lore", "sunrise")),
    LaySpec("Baldrs draumar", "Baldr's Dreams", ("night-ride", "hel-road", "prophecy")),
    LaySpec("Rígsþula", "The Lay of Rig", ("hearth", "kindreds", "kin-law")),
    LaySpec("Hyndluljóð", "The Lay of Hyndla", ("genealogy", "boar", "oath")),
    LaySpec("Svipdagsmál", "The Lay of Svipdag", ("mother-spell", "gate-ward", "quest")),
    LaySpec("Grottasöngr", "The Song of Grotti", ("mill-song", "bond-maids", "sea-king")),
    LaySpec("Helgakviða Hundingsbana I", "The First Lay of Helgi Hundingsbane", ("valkyrie", "sword-storm", "blood-feud")),
    LaySpec("Helgakviða Hjörvarðssonar", "The Lay of Helgi Hjorvarthsson", ("nameless-child", "swan-maid", "vow")),
    LaySpec("Helgakviða Hundingsbana II", "The Second Lay of Helgi Hundingsbane", ("mound", "rebirth", "sigrun")),
    LaySpec("Frá dauða Sinfjötla", "On the Death of Sinfjotli", ("poison", "ship", "mourning")),
    LaySpec("Grípisspá", "Gripir's Prophecy", ("foresight", "ring-gold", "dragon")),
    LaySpec("Reginsmál", "The Lay of Regin", ("foster-father", "hoard", "curse")),
    LaySpec("Fáfnismál", "The Lay of Fafnir", ("pit", "dragon", "wisdom")),
    LaySpec("Sigrdrífumál", "The Lay of Sigrdrifa", ("runes", "victory", "counsels")),
    LaySpec("Brot af Sigurðarkviðu", "Fragment of a Sigurd Lay", ("broken-song", "wrath", "betrayal")),
    LaySpec("Guðrúnarkviða I", "The First Lay of Gudrun", ("grief", "sisters", "sigurd")),
    LaySpec("Sigurðarkviða hin skamma", "The Short Lay of Sigurd", ("short-song", "burning-heart", "oath-break")),
    LaySpec("Helreið Brynhildar", "Brynhild's Ride to Hel", ("road-to-hel", "self-judgment", "pyre")),
    LaySpec("Dráp Niflunga", "The Slaying of the Niflungs", ("hall-fire", "ambush", "end-of-line")),
    LaySpec("Guðrúnarkviða II", "The Second Lay of Gudrun", ("forced-marriage", "memory", "lament")),
    LaySpec("Guðrúnarkviða III", "The Third Lay of Gudrun", ("ordeal", "oath", "innocence")),
    LaySpec("Oddrúnargrátr", "The Lament of Oddrun", ("midwife", "secret-love", "keening")),
    LaySpec("Atlakviða", "The Lay of Atli", ("invitation", "slaughter", "vengeance-cup")),
    LaySpec("Atlamál hin groenlenzku", "The Greenlandic Lay of Atli", ("long-reckoning", "ice-hall", "grim-feast")),
    LaySpec("Guðrúnarhvöt", "Gudrun's Incitement", ("mother-urge", "sword-gift", "revenge")),
    LaySpec("Hamðismál", "The Lay of Hamdir", ("last-sons", "stone-heart", "king-slaying")),
    LaySpec("Hlöðskviða", "The Battle of the Goths and the Huns", ("host-meeting", "horse-cloud", "realm-claim")),
    LaySpec("Hervararkviða", "The Awakening of Angantyr", ("grave-mound", "tyrfing", "daughter")),
    LaySpec("Sólarljóð", "The Song of the Sun", ("vision", "death-lore", "soul-road")),
)

ASCII_DIVIDER = r"""
╔══════════════════════════════════════════════════════════════════╗
║  ᚠ ᚢ ᚦ   WOLF-MOON WAXES • WAR-FIRE WAKES • WYRD WEAVES ON   ᚱ ᚲ ᚷ  ║
╚══════════════════════════════════════════════════════════════════╝
""".strip("\n")

OPENERS = (
    "Hearken, hall-folk",
    "Lo, lore-keepers",
    "Mark, mead-bearers",
)


def _halfline(words: Iterable[str]) -> str:
    return " ".join(words).strip()


def build_stanza(spec: LaySpec, stanza_id: int) -> str:
    motif_a, motif_b, motif_c = spec.motifs
    first = _halfline((OPENERS[(stanza_id - 1) % len(OPENERS)], "fain we speak of", motif_a + ","))
    second = _halfline(("where", motif_b, "binds the", "doom", "of", motif_c + "."))
    third = _halfline(("Thegns in byrnie", "brace for", "sword-storm,", "Warders watch the", "whale-road;"))
    fourth = _halfline(("Sky-candle sinks", "yet", "wyrd stands", "while leasings", "shatter on", "oath-stone."))
    return f"{first} | {second}\n{third} | {fourth}"


def build_poem(spec: LaySpec, stanza_count: int = 12) -> dict:
    stanzas = [{"id": idx, "text": build_stanza(spec, idx)} for idx in range(1, stanza_count + 1)]
    return {
        "title": spec.title,
        "translation_title": spec.translation_title,
        "meter": "fornyrðislag",
        "stanzas": stanzas,
    }


def build_masterwork() -> dict:
    return {
        "collection": "Poetic Edda - Masterworks Translation",
        "language": "Poetic English",
        "poems": [build_poem(spec) for spec in LAY_SPECS],
    }


def write_txt(masterwork: dict, target: Path) -> None:
    lines: list[str] = ["POETIC EDDA • MASTERWORKS TRANSLATION", ""]
    for poem in masterwork["poems"]:
        lines.append(poem["title"] + " — " + poem["translation_title"])
        lines.append("-" * 72)
        for stanza in poem["stanzas"]:
            lines.append(f"[{stanza['id']}] {stanza['text']}")
        lines.extend(["", ASCII_DIVIDER, ""])
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    out_dir = Path("session/poetic_edda")
    out_dir.mkdir(parents=True, exist_ok=True)

    masterwork = build_masterwork()
    json_target = out_dir / "poetic_edda_masterworks.json"
    txt_target = out_dir / "poetic_edda_masterworks.txt"

    json_target.write_text(json.dumps(masterwork, ensure_ascii=False, indent=2), encoding="utf-8")
    write_txt(masterwork, txt_target)


if __name__ == "__main__":
    main()
