import json
import os
import shutil
import sys
from datetime import datetime

import yaml


def load_yaml(file_path):
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(f"Error loading YAML file {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading file {file_path}: {e}")
        sys.exit(1)


def save_yaml(file_path, data):
    try:
        with open(file_path, "w") as file:
            yaml.dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
    except Exception as e:
        print(f"Error saving YAML file {file_path}: {e}")
        sys.exit(1)


def merge_proxies(new_proxies, old_proxies):
    try:
        # Check if both new_proxies and old_proxies have the 'proxies' key
        if "proxies" not in new_proxies or "proxies" not in old_proxies:
            raise ValueError("Both YAML files must contain a 'proxies' key")

        # Create a dictionary to store proxies with keys as proxy names
        merged_proxies = {proxy["name"]                          : proxy for proxy in old_proxies["proxies"]}
        new_proxies_added = False

        for proxy in new_proxies["proxies"]:
            if proxy["name"] not in merged_proxies:
                new_proxies_added = True
            merged_proxies[proxy["name"]] = proxy

        return {"proxies": list(merged_proxies.values())}, new_proxies_added
    except KeyError as e:
        print(f"Key error during merge: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Value error during merge: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during merge: {e}")
        sys.exit(1)


def compare_proxies(new_config, existing_config, print_proxies=False):
    new_proxies = {json.dumps(proxy, sort_keys=True)
                   for proxy in new_config["proxies"]}
    existing_proxies = {
        json.dumps(proxy, sort_keys=True) for proxy in existing_config["proxies"]
    }

    added_proxies = new_proxies - existing_proxies
    if added_proxies:
        if print_proxies:
            print("New proxies found:")
            for proxy in added_proxies:
                print(f"\n{json.loads(proxy)}")

        print(f"Total number of new proxies: {len(added_proxies)}")
        return True

    print("No update available")
    return False


def backup_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = f"{file_path}_{timestamp}.bcp"
        shutil.copy2(file_path, backup_path)
        print(f"Backup created at {backup_path}")


def main(new_proxies_path, old_proxies_path):
    # Load the YAML files
    new_proxies = load_yaml(new_proxies_path)
    old_proxies = load_yaml(old_proxies_path)

    # Merge proxies and get the result
    merged_proxies, new_proxies_added = merge_proxies(new_proxies, old_proxies)

    if new_proxies_added:
        # Create a backup of the old proxies file
        backup_file(old_proxies_path)

        # Save the merged proxies to the old proxies file
        save_yaml(old_proxies_path, merged_proxies)

        # Compare proxies and print new ones if any
        compare_proxies(new_proxies, merged_proxies, False)

        print(
            f"\nProxies from {new_proxies_path} have been merged into {old_proxies_path} without duplicates."
        )
    else:
        print("\nNo new proxies to merge. The existing file remains unchanged.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python append_proxies.py <new_proxies.yaml> <old_proxies.yaml>")
        sys.exit(1)

    new_proxies_path = sys.argv[1]
    old_proxies_path = sys.argv[2]
    main(new_proxies_path, old_proxies_path)
