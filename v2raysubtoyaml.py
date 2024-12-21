import base64
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import chardet
import requests
import yaml


def contains_letters(s):
    return bool(re.search("[a-zA-Z]", s))


def get_hostname(ip_address):
    try:
        hostname, alias, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror as e:
        print(f"Could not resolve hostname for IP {ip_address}: {e}")
        return None
    except Exception as e:
        print(
            f"An error occurred while resolving hostname for IP {ip_address}: {e}")
        return None


def decode_v2ray_subscription(url):
    response = requests.get(url)
    response_string = response.text
    try:
        if response.status_code == 200:
            if "vmess://" in response_string:
                return response_string

            try:
                decoded_data = base64.b64decode(
                    response_string).decode("utf-8")
                return decoded_data
            except Exception as e:
                print(f"\n{e}\n")
                print("Invalid format in url")
                return ""
        else:
            raise Exception(
                f"Failed to fetch V2Ray subscription from {url}. Status code: {response.status_code}"
            )
    except ValueError:
        print(f"Error in response_string {response_string}")
    except requests.exceptions.SSLError as e:
        print(
            f"SSL error occurred while fetching V2Ray subscription from {url}: {e}")
        print("Check your internet connection\n")
    except requests.exceptions.RequestException as e:
        print(
            f"An error occurred while fetching V2Ray subscription from {url}: {e}")


def clean_json_string(json_string):
    # Use a regex to find all key-value pairs where the value is quoted
    pattern = r'"([^"]*)"\s*:\s*"([^"]*)"'
    matches = re.findall(pattern, json_string)

    # Reconstruct a cleaned JSON string
    cleaned_data = (
        "{" + ", ".join([f'"{key}": "{value}"' for key,
                        value in matches]) + "}"
    )
    return cleaned_data


def extract_inactive_proxies(log_path):
    if not log_path or not os.path.exists(log_path):
        print("No log file provided or file does not exist.")
        return []

    inactive_entries = []
    uid_pattern = re.compile(r"uid: \{(.*?)\}")
    alive_status_pattern = re.compile(r"alive: false")

    try:
        with open(log_path, "r") as file:
            lines = file.readlines()
            for line in reversed(lines):
                if alive_status_pattern.search(line):
                    match = uid_pattern.search(line)
                    if match:
                        uid = match.group(1)
                        proxy_start = line.find("Health Checked, proxy: ") + len(
                            "Health Checked, proxy: "
                        )
                        proxy_end = line.find(", url: ")
                        proxy_name = line[proxy_start:proxy_end].strip()
                        if (
                            proxy_name not in inactive_entries
                            and proxy_name != "DIRECT"
                        ):
                            inactive_entries.append(proxy_name)
    except TypeError:
        return []

    return inactive_entries


def convert_v2ray_to_clash(decoded_data, inactive_proxies):
    v2ray_nodes = decoded_data.strip().split("\n")
    clash_config = {"proxies": []}
    invalid_host = []
    invalid_node = []
    inactive_online_proxies = []
    invalid_vmess = []

    for node in v2ray_nodes:
        if node.startswith("vmess://"):
            try:
                raw_data = base64.b64decode(node[8:])
            except ValueError:
                continue

            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            node_data = raw_data.decode(encoding, errors="ignore")
            cleaned_data = clean_json_string(node_data)

            try:
                node_json = json.loads(cleaned_data)
                proxy_name = node_json.get("ps", "Unnamed")

                # Skip dead proxies
                if proxy_name in inactive_proxies:
                    inactive_online_proxies.append(proxy_name)
                    continue

                server = node_json.get("add", "unknown")
                port = int(node_json.get("port", 443))
                host = node_json.get("host", "")
                network = node_json.get("net")

                if not host and contains_letters(server):
                    host = server
                elif "." not in host:
                    invalid_host.append(host)
                    continue

                if network != "ws":
                    continue

                clash_node = {
                    "name": proxy_name,
                    "server": server,
                    "port": port,
                    "type": node[:5],
                    "uuid": node_json.get("id", ""),
                    "alterId": int(node_json.get("aid", 0)),
                    "cipher": node_json.get("cipher", "auto"),
                    "tls": node_json.get("tls", "") == "tls",
                    "skip-cert-verify": node_json.get("skip-cert-verify", True),
                    "servername": host,
                    "network": network,
                    "ws-opts": {
                        "path": node_json.get("path", "/"),
                        "headers": {"Host": host},
                    },
                    "udp": node_json.get("udp", True),
                }
                clash_config["proxies"].append(clash_node)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {cleaned_data}")
                print(e)
                invalid_node.append(node)
            except KeyError as e:
                print(f"Missing key {e} in node: {cleaned_data}")
                invalid_node.append(node)

    info_to_print = {
        "Invalid_host": len(invalid_host),
        "Invalid_node": len(invalid_node),
        "Inactive online proxies": len(inactive_online_proxies),
        "Invalid vmess": len(invalid_vmess),
    }

    for key, count in info_to_print.items():
        if count:
            print(f"{key}: {count}", end=", ")

    return clash_config


def filter_proxies_by_port(config, port):
    filtered_proxies = [
        proxy for proxy in config["proxies"] if proxy.get("port") == port
    ]
    return {"proxies": filtered_proxies}


def update_server(config, new_server):
    for proxy in config["proxies"]:
        original_server_name = proxy["servername"]
        if not original_server_name:
            original_server = proxy["server"]
            proxy["servername"] = original_server
        proxy["server"] = new_server
    return config


def update_port(config, new_port):
    for proxy in config["proxies"]:
        original_port = proxy["port"]
        proxy["port"] = new_port
    return config


def save_yaml(file_path, data):
    if not data or not data.get("proxies"):
        print(f"No data to save for {file_path}\n")
        return

    try:
        with open(file_path, "w") as file:
            yaml.dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            print(f"Configuration has been written to {file_path}")
    except Exception as e:
        print(f"Error saving YAML file {file_path}: {e}")


def load_existing_proxies(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as file:
                return yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(f"Error reading YAML file {filename}: {e}")
            return {"proxies": []}
    else:
        return None


def compare_proxies(new_config, existing_config, print_proxies=False):
    new_proxies = {json.dumps(proxy, sort_keys=True)
                   for proxy in new_config["proxies"]}
    existing_proxies = {
        json.dumps(proxy, sort_keys=True) for proxy in existing_config["proxies"]
    }

    added_proxies = new_proxies - existing_proxies
    np_message = (
        "New proxies found:" if print_proxies else "Skipping printing new proxies..."
    )
    if added_proxies:
        print("New proxies found:")
        if print_proxies:
            for proxy in added_proxies:
                print(json.loads(proxy))

        print(f"Total number of new proxies: {len(added_proxies)}")
        return True

    print("No update available\n")
    return False


def get_base_filename(url):
    path_parts = url.replace("https://", "").replace("http://", "").split("/")
    if len(path_parts) >= 3:
        return f"{path_parts[1]}_{path_parts[2]}"
    else:
        raise ValueError(
            "URL does not contain enough parts to extract base filename")


def backup_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        backup_path = f"{file_path}_{timestamp}.bcp"
        shutil.copy2(file_path, backup_path)
        print(f"Backup created at {backup_path}")


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
    except ValueError as e:
        print(f"Value error during merge: {e}")
    except Exception as e:
        print(f"Unexpected error during merge: {e}")


def load_yaml(file_path):
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(f"Error loading YAML file {file_path}: {e}")
    except Exception as e:
        print(f"Unexpected error loading file {file_path}: {e}")


def append_proxies(new_proxies_path, old_proxies_path):
    # Load the YAML files
    new_proxies = load_yaml(new_proxies_path)
    old_proxies = load_yaml(old_proxies_path)

    # Merge proxies and get the result
    merged_proxies, new_proxies_added = merge_proxies(new_proxies, old_proxies)

    if new_proxies_added:
        # Compare proxies and print new ones if any
        if compare_proxies(merged_proxies, old_proxies, False):
            # Create a backup of the old proxies file
            backup_file(old_proxies_path)

        # Save the merged proxies to the old proxies file
        save_yaml(old_proxies_path, merged_proxies)

        print(
            f"Proxies from {new_proxies_path} have been merged into {old_proxies_path} without duplicates.\n"
        )
    else:
        print("No new proxies to merge. The existing file remains unchanged.\n")


def main(log_path=None):
    urls = [
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/resasanian/Mirza/main/vmess",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/splitted/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/bulk-xray-v2ray-vless-vmess-...-configs/main/sub/United%20States/config.txt",
    ]
    # Extract inactive proxies from log file if provided
    inactive_proxies = extract_inactive_proxies(log_path) if log_path else []

    for url in urls:
        print(f"> Processing {url}")
        decoded_data = decode_v2ray_subscription(url)
        if decoded_data is None:
            continue

        # Pass inactive proxies to the conversion function
        clash_config = convert_v2ray_to_clash(decoded_data, inactive_proxies)

        try:
            folder_name_base = f"proxies/{get_base_filename(url)}"
            directory = Path(folder_name_base)
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
        except ValueError as e:
            print(f"Skipping URL {url}: {e}")
            continue

        existing_proxies = load_existing_proxies(
            f"{folder_name_base}/proxies.yaml")

        if existing_proxies:
            if not compare_proxies(clash_config, existing_proxies):
                continue

        save_yaml(f"{folder_name_base}/proxies.yaml", clash_config)

        proxies_port_80 = filter_proxies_by_port(clash_config, 80)
        save_yaml(f"{folder_name_base}/proxies_port_80.yaml", proxies_port_80)

        proxies_port_443 = filter_proxies_by_port(clash_config, 443)
        save_yaml(f"{folder_name_base}/proxies_port_443.yaml",
                  proxies_port_443)

        new_server = "104.26.6.171"  # Replace with new server IP or hostname
        updated_config_80 = update_server(proxies_port_80, new_server)
        save_yaml(f"{folder_name_base}/proxies_updated_80.yaml",
                  updated_config_80)

        updated_config_443 = update_server(proxies_port_443, new_server)
        save_yaml(f"{folder_name_base}/proxies_updated_443.yaml",
                  updated_config_443)

        updated_port = update_port(clash_config, 80)
        updated_config_and_port = update_server(updated_port, new_server)
        save_yaml(f"{folder_name_base}/updated_port.yaml",
                  updated_config_and_port)


if __name__ == "__main__":
    # Optionally allow a log file to be passed via command-line arguments
    import argparse

    # Optionally allow a log file to be passed via command-line arguments
    parser = argparse.ArgumentParser(
        description="Process V2Ray URLs and convert to Clash format."
    )
    parser.add_argument(
        "old_proxies",
        type=str,
        nargs="?",
        help="Path to the old proxies YAML file (optional).",
    )
    parser.add_argument(
        "--log",
        type=str,
        help="Path to the log file containing inactive proxies (optional)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append new proxies to the old ones",
    )

    args = parser.parse_args()

    # Get the log file path if provided
    log_file_path = args.log if args.log else None
    main(log_file_path)

    # Call append_proxies if the --append flag was used
    if args.append:
        # Set default paths if arguments are not provided
        old_proxies_path = args.old_proxies
        # Loop through and append proxies
        for proxy in glob.glob("./proxies/*/updated_port.yaml"):
            print(f"> Appending {proxy} to {old_proxies_path}...")
            # Call the append_proxies.py script with the proxy and proxies_file as arguments
            new_proxies_path = proxy

            # Check if the provided file paths exist
            if not os.path.exists(new_proxies_path):
                print(
                    f"Error: The new proxies file '{new_proxies_path}' does not exist."
                )
                exit(1)

            if not os.path.exists(old_proxies_path):
                print(
                    f"Error: The old proxies file '{old_proxies_path}' does not exist."
                )
                exit(1)

            append_proxies(new_proxies_path, old_proxies_path)
