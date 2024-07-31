import sys
import yaml
import shutil
import os

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def save_yaml(file_path, data):
    with open(file_path, 'w') as file:
        yaml.dump(data, file, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)

def merge_proxies(new_proxies, old_proxies):
    merged_proxies = {proxy['name']: proxy for proxy in old_proxies['proxies']}
    for proxy in new_proxies['proxies']:
        if proxy['name'] not in merged_proxies:
            merged_proxies[proxy['name']] = proxy
    return {'proxies': list(merged_proxies.values())}

def backup_file(file_path):
    if os.path.exists(file_path):
        backup_path = f"{file_path}.bcp"
        shutil.copy2(file_path, backup_path)
        print(f"Backup created at {backup_path}")

def main(new_proxies_path, old_proxies_path):
    # Create a backup of the old proxies file
    backup_file(old_proxies_path)

    # Load the YAML files
    new_proxies = load_yaml(new_proxies_path)
    old_proxies = load_yaml(old_proxies_path)

    # Merge proxies and save the result
    merged_proxies = merge_proxies(new_proxies, old_proxies)
    save_yaml(old_proxies_path, merged_proxies)
    print(f"Proxies from {new_proxies_path} have been merged into {old_proxies_path} without duplicates.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python append_proxies.py <new_proxies.yaml> <old_proxies.yaml>")
        sys.exit(1)

    new_proxies_path = sys.argv[1]
    old_proxies_path = sys.argv[2]
    main(new_proxies_path, old_proxies_path)
