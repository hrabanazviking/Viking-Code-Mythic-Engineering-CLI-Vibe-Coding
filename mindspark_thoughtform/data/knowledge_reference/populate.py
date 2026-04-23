import urllib.request
import urllib.parse
import json
import time
import sys
from pathlib import Path

def fetch_category_members(category, max_results=5000):
    """Recursively fetch article titles from a Wikipedia category."""
    titles = set()
    categories_to_check = [category]
    checked_categories = set()

    print(f"Discovering up to {max_results} articles for category: {category}...")

    while categories_to_check and len(titles) < max_results:
        current_cat = categories_to_check.pop(0)
        if current_cat in checked_categories:
            continue
        checked_categories.add(current_cat)

        url = f"https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:{urllib.parse.quote(current_cat)}&cmlimit=500&format=json"
        
        while True:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'SigridKnowledgeBuilder/1.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    
                    for member in data['query'].get('categorymembers', []):
                        if member['ns'] == 0:  # Article
                            titles.add(member['title'])
                            if len(titles) >= max_results:
                                return list(titles)
                        elif member['ns'] == 14:  # Subcategory
                            cat_name = member['title'].replace("Category:", "")
                            if cat_name not in checked_categories:
                                categories_to_check.append(cat_name)

                    if 'continue' in data:
                        cont_token = data['continue']['cmcontinue']
                        url = f"https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:{urllib.parse.quote(current_cat)}&cmlimit=500&cmcontinue={urllib.parse.quote(cont_token)}&format=json"
                    else:
                        break
            except Exception as e:
                print(f"Error fetching category {current_cat}: {e}")
                break
            time.sleep(0.1) # Be polite to API

    return list(titles)

def fetch_extracts_in_batches(titles, batch_size=20):
    """Fetch article summaries in batches to be efficient."""
    results = {}
    for i in range(0, len(titles), batch_size):
        batch = titles[i:i+batch_size]
        titles_param = "|".join(urllib.parse.quote(t) for t in batch)
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={titles_param}&format=json"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SigridKnowledgeBuilder/1.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                pages = data['query']['pages']
                for page_id, page_data in pages.items():
                    if 'extract' in page_data and page_data['extract'].strip():
                        results[page_data['title']] = page_data['extract'].strip()
        except Exception as e:
            print(f"Error fetching batch: {e}")
        time.sleep(0.1)
    return results

def populate_file(filename, category, display_name):
    print(f"\n--- Starting population for {display_name} ({filename}) ---")
    titles = fetch_category_members(category, max_results=1000) # Capped at 1000 for this run to ensure we finish in time, but extremely dense.
    print(f"Found {len(titles)} articles. Fetching content...")
    
    extracts = fetch_extracts_in_batches(titles)
    
    content = f"# 📚 {display_name}: Comprehensive Knowledge Base\n\n"
    content += f"> **Source:** Curated historical and technical data.\n> **Total Entries:** {len(extracts)}\n\n---\n\n"
    
    count = 1
    for title, extract in extracts.items():
        # Clean up newlines in extract
        clean_extract = extract.replace('\n', ' ')
        content += f"## {count}. {title}\n"
        content += f"{clean_extract}\n\n"
        count += 1
        
    filepath = Path(__file__).resolve().parent / filename
    filepath.write_text(content, encoding='utf-8')
    print(f"Successfully wrote {len(extracts)} real entries to {filename}.")

if __name__ == "__main__":
    targets = [
        ("VIKING_HISTORY.md", "Viking_Age", "Viking History & The Viking Age"),
        ("OLD_NORSE.md", "Runology", "Old Norse Language & Runology"),
        ("ARTIFICIAL_INTELLIGENCE.md", "Artificial_intelligence", "Artificial Intelligence"),
        ("SOFTWARE_ENGINEERING.md", "Software_engineering", "Software Engineering"),
        ("DATA_SCIENCE.md", "Data_science", "Data Science"),
        ("CYBERSECURITY.md", "Computer_security", "Cybersecurity"),
        ("NETWORKING.md", "Computer_networking", "Computer Networking")
    ]
    
    for filename, cat, display in targets:
        populate_file(filename, cat, display)
