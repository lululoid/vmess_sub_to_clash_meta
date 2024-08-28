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


def extract_inactive_proxies(filename):
    inactive_entries = []
    uid_pattern = re.compile(r"uid: \{(.*?)\}")
    alive_status_pattern = re.compile(r"alive: false")

    try:
        with open(filename, "r") as file:
            lines = file.readlines()
            # Process lines in reverse order to make sure it's start from the most recent test first
            for line in reversed(lines):
                if alive_status_pattern.search(line):
                    match = uid_pattern.search(line)
                    if match:
                        uid = match.group(1)
                        # Extracting proxy name from the line
                        proxy_start = line.find("proxy: ") + len("proxy: ")
                        proxy_end = line.find(", url: ")
                        proxy_name = line[proxy_start:proxy_end].strip()
                        if (
                            proxy_name not in inactive_entries
                            and proxy_name != "DIRECT"
                        ):
                            inactive_entries.append(proxy_name)
    except TypeError:
        return ""

    return inactive_entries


def clean_proxies(proxies_data):
    cleaned_proxies = []
    inactive_proxies = extract_inactive_proxies(log_path)

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


def main(proxies_path, log_path=None):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    cleaned_proxies_data = clean_proxies(proxies_data["proxies"])

    save_yaml(proxies_path, cleaned_proxies_data)

    if log_path:
        # Optionally handle logging here, e.g., save logs to log_path
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python clean_proxies.py <proxies.yaml> [log_path]")
        sys.exit(1)

    proxies_path = sys.argv[1]
    log_path = sys.argv[2] if len(sys.argv) == 3 else None

    main(proxies_path, log_path)
