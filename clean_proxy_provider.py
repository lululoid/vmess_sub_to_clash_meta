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


def clean_proxies(proxies_data):
    cleaned_proxies = []
    for proxy in proxies_data:
        servername = proxy.get("servername")
        host = proxy.get("ws-opts", {}).get("headers", {}).get("Host")
        path = proxy.get("path")

        if not servername or servername in ("", None):
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

    return {"proxies": cleaned_proxies}


def main(proxies_path):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    cleaned_proxies_data = clean_proxies(proxies_data["proxies"])

    save_yaml(proxies_path, cleaned_proxies_data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean_proxies.py <proxies.yaml>")
        sys.exit(1)

    proxies_path = sys.argv[1]
    main(proxies_path)
