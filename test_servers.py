import socket
import sys
import time

import yaml
from tqdm import tqdm


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


def test_server(server, port, timeout=5):
    try:
        with socket.create_connection((server, port), timeout) as sock:
            return True
    except (socket.timeout, socket.error) as e:
        if isinstance(e, socket.timeout):
            return False
        else:
            raise


def remove_unreachable_proxies(proxies):
    reachable_proxies = []
    unreachable_proxies = []
    results = []

    with tqdm(total=len(proxies), unit="proxy",) as pbar:
        for proxy in proxies:
            server_name = proxy.get("servername")
            port = proxy.get("port")
            if server_name and port:
                try:
                    is_reachable = test_server(server_name, port)
                except socket.error:
                    tqdm.write("Network error occurred. Retrying...")
                    time.sleep(5)  # Wait and retry
                    try:
                        is_reachable = test_server(server_name, port)
                    except socket.error:
                        is_reachable = False
                if is_reachable:
                    reachable_proxies.append(proxy)
                else:
                    unreachable_proxies.append(proxy)
                results.append(
                    (proxy.get("name"), server_name, port, is_reachable))
                pbar.update(1)
                time.sleep(
                    0.5
                )  # To simulate some delay and make the progress bar more visible
            else:
                print(f"Invalid proxy configuration: {proxy}")

    print("\nServer Test Results:")
    for name, server_name, port, is_reachable in results:
        status = "Reachable" if is_reachable else "Unreachable"
        print(
            f"- Proxy: {name}\n  server_name: {server_name}\n  Port: {port} - {status}"
        )

    print(f"\nReachable Proxies ({len(reachable_proxies)}):")
    for proxy in reachable_proxies:
        proxy_name = proxy.get("name")
        print(f"- {proxy_name}")

    print(f"\nUnreachable Proxies ({len(unreachable_proxies)}):")
    for proxy in unreachable_proxies:
        proxy_name = proxy.get("name")
        print(f"- {proxy_name}")

    return reachable_proxies


def main(proxies_path):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    proxies = proxies_data["proxies"]
    reachable_proxies = remove_unreachable_proxies(proxies)

    proxies_data["proxies"] = reachable_proxies
    save_yaml(proxies_path, proxies_data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_servers.py <proxies.yaml>")
        sys.exit(1)

    proxies_path = sys.argv[1]
    main(proxies_path)
