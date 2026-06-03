#!/usr/bin/env python3
"""
Diagnostic System v3.0 - Debug and Troubleshooting Tools
=========================================================

Run this to check system health, find issues, and generate debug reports.
Usage: python diagnostics.py [--full] [--fix]
"""

import sys
import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


class DiagnosticSystem:
    """Comprehensive diagnostic and troubleshooting tools."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.info: List[Dict] = []
        
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all diagnostic checks."""
        print("=" * 60)
        print("  NORSE SAGA ENGINE - DIAGNOSTIC REPORT")
        print("=" * 60)
        print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Run checks
        results["checks"]["python"] = self.check_python()
        results["checks"]["dependencies"] = self.check_dependencies()
        results["checks"]["config"] = self.check_config()
        results["checks"]["directories"] = self.check_directories()
        results["checks"]["data_files"] = self.check_data_files()
        results["checks"]["characters"] = self.check_characters()
        results["checks"]["sessions"] = self.check_sessions()
        results["checks"]["memory"] = self.check_memory_system()
        results["checks"]["auto_generated"] = self.check_auto_generated()
        
        # Summary
        results["issues"] = self.issues
        results["warnings"] = self.warnings
        results["info"] = self.info
        
        self.print_summary()
        
        return results
    
    def check_python(self) -> Dict:
        """Check Python version and environment."""
        print("[1/9] Checking Python environment...")
        
        result = {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
            "ok": True
        }
        
        version_info = sys.version_info
        if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 10):
            self.issues.append({
                "category": "python",
                "message": f"Python 3.10+ required, found {version_info.major}.{version_info.minor}",
                "fix": "Install Python 3.10 or newer"
            })
            result["ok"] = False
        else:
            print(f"  [OK] Python {version_info.major}.{version_info.minor}.{version_info.micro}")
        
        return result
    
    def check_dependencies(self) -> Dict:
        """Check required dependencies."""
        print("[2/9] Checking dependencies...")
        
        required = {
            "yaml": "PyYAML",
            "rich": "rich",
            "httpx": "httpx",
            "pydantic": "pydantic",
        }
        
        optional = {
            "replicate": "replicate",
            "PIL": "Pillow",
            "jsonlines": "jsonlines",
        }
        
        result = {"required": {}, "optional": {}, "ok": True}
        
        for module, package in required.items():
            try:
                __import__(module)
                result["required"][package] = "installed"
                print(f"  [OK] {package}")
            except ImportError:
                result["required"][package] = "missing"
                result["ok"] = False
                self.issues.append({
                    "category": "dependencies",
                    "message": f"Required package missing: {package}",
                    "fix": f"pip install {package}"
                })
                print(f"  [ERROR] {package} (MISSING)")
        
        for module, package in optional.items():
            try:
                __import__(module)
                result["optional"][package] = "installed"
                print(f"  [OK] {package} (optional)")
            except ImportError:
                result["optional"][package] = "missing"
                self.warnings.append({
                    "category": "dependencies",
                    "message": f"Optional package missing: {package}",
                    "fix": f"pip install {package}"
                })
                print(f"  - {package} (optional, not installed)")
        
        return result
    
    def check_config(self) -> Dict:
        """Check configuration file."""
        print("[3/9] Checking configuration...")
        
        config_path = self.base_path / "config.yaml"
        template_path = self.base_path / "config.template.yaml"
        
        result = {"exists": False, "valid": False, "api_keys": {}, "ok": True}
        
        if not config_path.exists():
            if template_path.exists():
                self.issues.append({
                    "category": "config",
                    "message": "config.yaml not found",
                    "fix": "Copy config.template.yaml to config.yaml and add your API keys"
                })
                print("  [ERROR] config.yaml not found")
            else:
                self.issues.append({
                    "category": "config",
                    "message": "Neither config.yaml nor config.template.yaml found",
                    "fix": "Reinstall the game or create config.yaml manually"
                })
                print("  [ERROR] No config files found")
            result["ok"] = False
            return result
        
        result["exists"] = True
        print("  [OK] config.yaml exists")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            result["valid"] = True
            print("  [OK] config.yaml is valid YAML")
        except Exception as e:
            self.issues.append({
                "category": "config",
                "message": f"config.yaml is invalid: {e}",
                "fix": "Check YAML syntax (indentation, colons, quotes)"
            })
            print(f"  [ERROR] config.yaml invalid: {e}")
            result["ok"] = False
            return result
        
        # Check API keys
        openrouter_key = config.get("openrouter", {}).get("api_key", "")
        if openrouter_key and openrouter_key != "your-openrouter-api-key-here":
            result["api_keys"]["openrouter"] = "configured"
            print("  [OK] OpenRouter API key configured")
        else:
            result["api_keys"]["openrouter"] = "missing"
            self.issues.append({
                "category": "config",
                "message": "OpenRouter API key not configured",
                "fix": "Add your OpenRouter API key to config.yaml"
            })
            print("  [ERROR] OpenRouter API key missing")
            result["ok"] = False
        
        replicate_key = config.get("replicate", {}).get("api_key", "")
        if replicate_key and replicate_key != "your-replicate-api-key-here":
            result["api_keys"]["replicate"] = "configured"
            print("  [OK] Replicate API key configured (optional)")
        else:
            result["api_keys"]["replicate"] = "not configured"
            print("  - Replicate API key not configured (optional)")
        
        return result
    
    def check_directories(self) -> Dict:
        """Check required directories."""
        print("[4/9] Checking directories...")
        
        required_dirs = [
            "data",
            "data/characters",
            "data/charts",
            "data/world",
            "data/quests",
            "data/sessions",
            "data/memory",
            "data/auto_generated",
            "data/auto_generated/characters",
            "data/auto_generated/quests",
            "data/auto_generated/locations",
            "logs",
        ]
        
        result = {"directories": {}, "ok": True}
        
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if full_path.exists():
                result["directories"][dir_path] = "exists"
                print(f"  [OK] {dir_path}/")
            else:
                result["directories"][dir_path] = "missing"
                self.warnings.append({
                    "category": "directories",
                    "message": f"Directory missing: {dir_path}",
                    "fix": f"mkdir -p {dir_path}"
                })
                print(f"  - {dir_path}/ (will be created)")
                # Auto-create
                full_path.mkdir(parents=True, exist_ok=True)
        
        return result
    
    def check_data_files(self) -> Dict:
        """Check essential data files."""
        print("[5/9] Checking data files...")
        
        essential_files = [
            "data/charts/elder_futhark.yaml",
            "data/charts/gm_mindset.yaml",
            "data/charts/viking_values.yaml",
            "data/world/cities/uppsala.yaml",
        ]
        
        result = {"files": {}, "ok": True}
        
        for file_path in essential_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                result["files"][file_path] = "exists"
                print(f"  [OK] {file_path}")
            else:
                result["files"][file_path] = "missing"
                self.issues.append({
                    "category": "data",
                    "message": f"Essential file missing: {file_path}",
                    "fix": "Reinstall the game or restore from backup"
                })
                print(f"  [ERROR] {file_path} (MISSING)")
                result["ok"] = False
        
        # Count chart files
        charts_path = self.base_path / "data" / "charts"
        if charts_path.exists():
            chart_count = len(list(charts_path.glob("*.yaml")))
            self.info.append({
                "category": "data",
                "message": f"Found {chart_count} chart files"
            })
            print(f"  [INFO] {chart_count} chart files loaded")
        
        return result
    
    def check_characters(self) -> Dict:
        """Check character files."""
        print("[6/9] Checking character files...")
        
        result = {
            "player_characters": 0,
            "npcs": 0,
            "auto_generated": 0,
            "schema_issues": [],
            "ok": True
        }
        
        # Count player characters
        pc_path = self.base_path / "data" / "characters" / "player_characters"
        if pc_path.exists():
            result["player_characters"] = len(list(pc_path.glob("*.yaml")))
        
        # Count NPCs
        npc_path = self.base_path / "data" / "characters" / "npcs"
        if npc_path.exists():
            result["npcs"] = len(list(npc_path.rglob("*.yaml")))
        
        # Count auto-generated
        auto_path = self.base_path / "data" / "auto_generated" / "characters"
        if auto_path.exists():
            result["auto_generated"] = len(list(auto_path.glob("*.yaml")))
        
        print(f"  [OK] {result['player_characters']} player characters")
        print(f"  [OK] {result['npcs']} NPCs")
        print(f"  [OK] {result['auto_generated']} auto-generated characters")
        
        # Check for schema issues
        if result["player_characters"] == 0:
            self.warnings.append({
                "category": "characters",
                "message": "No player characters found",
                "fix": "Create a character in data/characters/player_characters/"
            })
        
        return result
    
    def check_sessions(self) -> Dict:
        """Check session files."""
        print("[7/9] Checking sessions...")
        
        sessions_path = self.base_path / "data" / "sessions"
        result = {"sessions": [], "ok": True}
        
        if not sessions_path.exists():
            print("  - No sessions directory")
            return result
        
        for session_dir in sessions_path.iterdir():
            if session_dir.is_dir():
                state_file = session_dir / "state.yaml"
                if state_file.exists():
                    result["sessions"].append(session_dir.name)
        
        if result["sessions"]:
            print(f"  [OK] {len(result['sessions'])} saved sessions found")
            for sid in result["sessions"][:3]:
                print(f"    - {sid}")
            if len(result["sessions"]) > 3:
                print(f"    ... and {len(result['sessions']) - 3} more")
        else:
            print("  - No saved sessions")
        
        return result
    
    def check_memory_system(self) -> Dict:
        """Check memory system files."""
        print("[8/9] Checking memory system...")
        
        memory_path = self.base_path / "data" / "memory"
        result = {"memory_files": 0, "ok": True}
        
        if memory_path.exists():
            result["memory_files"] = len(list(memory_path.glob("*_memory.json")))
        
        if result["memory_files"] > 0:
            print(f"  [OK] {result['memory_files']} memory files found")
        else:
            print("  - No memory files (normal for new install)")
        
        return result
    
    def check_auto_generated(self) -> Dict:
        """Check auto-generated content."""
        print("[9/9] Checking auto-generated content...")
        
        auto_path = self.base_path / "data" / "auto_generated"
        result = {
            "characters": 0,
            "quests": 0,
            "locations": 0,
            "portraits": 0,
            "ok": True
        }
        
        if auto_path.exists():
            chars = auto_path / "characters"
            if chars.exists():
                result["characters"] = len(list(chars.glob("*.yaml")))
            
            quests = auto_path / "quests"
            if quests.exists():
                result["quests"] = len(list(quests.glob("*.yaml")))
            
            locs = auto_path / "locations"
            if locs.exists():
                result["locations"] = len(list(locs.glob("*.yaml")))
            
            portraits = auto_path / "portraits"
            if portraits.exists():
                result["portraits"] = len(list(portraits.glob("*.png"))) + len(list(portraits.glob("*.jpg")))
        
        print(f"  [OK] {result['characters']} auto-generated characters")
        print(f"  [OK] {result['quests']} auto-generated quests")
        print(f"  [OK] {result['locations']} auto-generated locations")
        print(f"  [OK] {result['portraits']} auto-generated portraits")
        
        return result
    
    def print_summary(self):
        """Print summary of issues and warnings."""
        print()
        print("=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        
        if self.issues:
            print(f"\n[ERROR] ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  [{issue['category']}] {issue['message']}")
                print(f"    Fix: {issue['fix']}")
        
        if self.warnings:
            print(f"\n[WARNING] WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                print(f"  [{warn['category']}] {warn['message']}")
                if warn.get('fix'):
                    print(f"    Fix: {warn['fix']}")
        
        if not self.issues and not self.warnings:
            print("\n[SUCCESS] All checks passed! System is healthy.")
        elif not self.issues:
            print(f"\n[SUCCESS] No critical issues. {len(self.warnings)} warnings to review.")
        else:
            print(f"\n[ERROR] {len(self.issues)} issues need to be fixed.")
        
        print()
    
    def save_report(self, filepath: str = "diagnostic_report.json"):
        """Save diagnostic report to file."""
        results = self.run_all_checks()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Report saved to: {filepath}")
        return results
    
    def auto_fix(self) -> List[str]:
        """Attempt to automatically fix issues."""
        fixes_applied = []
        
        print("\nAttempting automatic fixes...")
        
        # Create missing directories
        required_dirs = [
            "data/auto_generated/characters",
            "data/auto_generated/quests",
            "data/auto_generated/locations",
            "data/auto_generated/portraits",
            "data/memory",
            "data/sessions",
            "logs",
        ]
        
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                fixes_applied.append(f"Created directory: {dir_path}")
                print(f"  [OK] Created {dir_path}/")
        
        # Create config from template if missing
        config_path = self.base_path / "config.yaml"
        template_path = self.base_path / "config.template.yaml"
        
        if not config_path.exists() and template_path.exists():
            import shutil
            shutil.copy(template_path, config_path)
            fixes_applied.append("Created config.yaml from template")
            print("  [OK] Created config.yaml from template")
            print("    (You still need to add your API keys!)")
        
        if fixes_applied:
            print(f"\n[SUCCESS] Applied {len(fixes_applied)} fixes")
        else:
            print("\n[SUCCESS] No automatic fixes needed")
        
        return fixes_applied


def main():
    """Run diagnostics."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Norse Saga Engine Diagnostics")
    parser.add_argument("--full", action="store_true", help="Run full diagnostics")
    parser.add_argument("--fix", action="store_true", help="Attempt automatic fixes")
    parser.add_argument("--save", type=str, help="Save report to file")
    
    args = parser.parse_args()
    
    diag = DiagnosticSystem()
    
    if args.fix:
        diag.auto_fix()
    
    if args.save:
        diag.save_report(args.save)
    else:
        diag.run_all_checks()


if __name__ == "__main__":
    main()
