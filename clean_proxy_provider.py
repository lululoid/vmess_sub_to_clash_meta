import re
import sys

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
    if data and "proxies" in data and data["proxies"]:
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
                print(f"Configuration has been written to {file_path}")
        except Exception as e:
            print(f"Error saving YAML file {file_path}: {e}")
            sys.exit(1)
    else:
        print(f"No valid data to save to {file_path}")


def extract_inactive_uids(filename):
    inactive_entries = []
    uid_pattern = re.compile(r"uid: \{(.*?)\}")
    alive_status_pattern = re.compile(r"alive: false")

    with open(filename, "r") as file:
        for line in file:
            if alive_status_pattern.search(line):
                match = uid_pattern.search(line)
                if match:
                    uid = match.group(1)
                    # Extracting proxy name from the line
                    proxy_start = line.find("proxy: ") + len("proxy: ")
                    proxy_end = line.find(", url: ")
                    proxy_name = line[proxy_start:proxy_end].strip()
                    inactive_entries.append(proxy_name)

    return inactive_entries


def clean_proxies(proxies_data):
    cleaned_proxies = []
    inactive_proxies = extract_inactive_uids(log_path)

    for proxy in proxies_data:
        servername = proxy.get("servername")
        host = proxy.get("ws-opts", {}).get("headers", {}).get("Host")
        path = proxy.get("path")
        proxy_name = proxy.get("name")
        proxy_dead = proxy_name in inactive_proxies

        if proxy_dead:
            continue
        elif not servername or servername in ("", None):
            if host and host not in ("", None):
                if path and path not in ("", None):
                    proxy["servername"] = host
                    cleaned_proxies.append(proxy)
            else:
                print(
                    f"Removing proxy with name {proxy.get('name')} due to missing servername and Host"
                )
        else:
            cleaned_proxies.append(proxy)

    print(f"Number of dead proxies: {len(inactive_proxies)}")
    return {"proxies": cleaned_proxies}


def main(proxies_path, log_path):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    cleaned_proxies_data = clean_proxies(proxies_data["proxies"])

    save_yaml(proxies_path, cleaned_proxies_data)


if __name__ == "__main__":
    if len(sys.argv) > 3:
        print("Usage: python clean_proxies.py <proxies.yaml>")
        sys.exit(1)

    proxies_path = sys.argv[1]
    log_path = sys.argv[2]
    main(proxies_path, log_path)
