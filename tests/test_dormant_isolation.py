import sys
import unittest

class DormantIsolationTests(unittest.TestCase):
    def test_cli_import_does_not_load_dormant_modules(self):
        # We start by importing the main cli entrypoint
        # to trigger all standard startup imports and command discovery.
        import mythic_vibe_cli.cli

        # List of top-level modules from the root that are considered dormant
        dormant_modules = {
            "ai",
            "core",
            "systems",
            "sessions",
            "yggdrasil",
            "mindspark_thoughtform",
            "ollama",
            "whisper",
            "chatterbox",
            # We don't check for 'imports' since that's a very common generic word,
            # but we can check if there are specific legacy modules if needed.
        }

        # Check sys.modules for any leakage
        leaked = []
        for mod_name in list(sys.modules.keys()):
            top_level = mod_name.split(".")[0]
            if top_level in dormant_modules:
                # If it's a dormant module, it should only be here if it's explicitly 
                # allowed. Currently, no dormant modules should be loaded during active
                # runtime startup without the island flag being enabled.
                leaked.append(mod_name)

        self.assertFalse(
            leaked,
            f"Active CLI runtime leaked dormant modules into sys.modules: {leaked}. "
            f"Dormant code must be isolated from standard execution paths."
        )

if __name__ == "__main__":
    unittest.main()
