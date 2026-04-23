import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Regex pattern to match Windows absolute paths
PATH_PATTERN = r'[A-Za-z]:[\\/][^\s\\/].*'

def replace_absolute_paths(file_path: Path):
    """Replace absolute paths with relative paths in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all absolute paths
        abs_paths = re.findall(PATH_PATTERN, content)
        if not abs_paths:
            return
        
        # Replace each absolute path with relative path
        for abs_path in set(abs_paths):
            abs_path = abs_path.strip("'\"")
            try:
                rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
                # Normalize path separators
                rel_path = rel_path.replace('\\', '/')
                content = content.replace(abs_path, rel_path)
            except ValueError:
                # Path outside project scope - remove absolute reference
                content = content.replace(abs_path, '')
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Processed {file_path}")
    
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def main():
    # Process all files in project
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(('.py', '.md', '.yaml', '.json', '.txt')):
                file_path = Path(root) / file
                replace_absolute_paths(file_path)

if __name__ == "__main__":
    main()