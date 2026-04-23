import sys
import os
import json

# Add the directory containing this script to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Determine the repository root
repo_root = os.path.abspath(os.path.join(script_dir, '..'))

try:
    from edda_translations import voluspa
    from edda_translations import havamal
    from edda_translations import vafthrudnismal
    from edda_translations import grimnismal
    from edda_translations import thrymskvida
    from edda_translations import skirnismal
    from edda_translations import harbardsljod
    from edda_translations import hymiskvida
    from edda_translations import lokasenna
    from edda_translations import volundarkvida
    from edda_translations import alvissmal
    from edda_translations import heroic_poems
    from edda_translations import heroic_poems_2
    from edda_translations import heroic_poems_3
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def main():
    edda_data = {
        "metadata": {
            "title": "The Poetic Edda",
            "translator": "Jules (AI) for Norse Saga Engine",
            "style": "Authentic 9th Century Viking Values, Alliterative Verse",
            "source": "Composite of Codex Regius and other manuscripts",
            "date": "2024",
            "description": "A comprehensive translation of the Poetic Edda, focusing on archaic beauty, Germanic roots, and traditional structure."
        },
        "poems": []
    }

    print("Compiling Poetic Edda...")

    # Add Mythological Poems
    print("Adding Völuspá...")
    edda_data["poems"].append(voluspa.get_poem())
    print("Adding Hávamál...")
    edda_data["poems"].append(havamal.get_poem())
    print("Adding Vafþrúðnismál...")
    edda_data["poems"].append(vafthrudnismal.get_poem())
    print("Adding Grímnismál...")
    edda_data["poems"].append(grimnismal.get_poem())
    print("Adding Skírnismál...")
    edda_data["poems"].append(skirnismal.get_poem())
    print("Adding Hárbarðsljóð...")
    edda_data["poems"].append(harbardsljod.get_poem())
    print("Adding Hymiskviða...")
    edda_data["poems"].append(hymiskvida.get_poem())
    print("Adding Lokasenna...")
    edda_data["poems"].append(lokasenna.get_poem())
    print("Adding Þrymskviða...")
    edda_data["poems"].append(thrymskvida.get_poem())
    print("Adding Völundarkviða...")
    edda_data["poems"].append(volundarkvida.get_poem())
    print("Adding Alvíssmál...")
    edda_data["poems"].append(alvissmal.get_poem())

    # Add Heroic Poems (list)
    print("Adding Heroic Poems...")
    edda_data["poems"].extend(heroic_poems.get_poems())
    print("Adding More Heroic Poems...")
    edda_data["poems"].extend(heroic_poems_2.get_poems())
    print("Adding Miscellaneous Poems...")
    edda_data["poems"].extend(heroic_poems_3.get_poems())

    # Output path is NorseSagaEngine_v3.4.0/data/Poetic_Edda_Translation.json
    output_path = os.path.join(repo_root, 'data/Poetic_Edda_Translation.json')

    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Writing to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(edda_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote Poetic Edda translation to {output_path}")

if __name__ == "__main__":
    main()
