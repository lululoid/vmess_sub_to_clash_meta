import base64
import json
import os
import re
import socket
import sys
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
    try:
        response = requests.get(url)
        response_string = response.text
        if response.status_code == 200:
            try:
                decoded_data = base64.b64decode(
                    response_string).decode("utf-8")
                return decoded_data
            except UnicodeDecodeError:
                if "vmess://" in response_string:
                    return response_string
                raise Exception("Invalid format in url")
        else:
            raise Exception(
                f"Failed to fetch V2Ray subscription from {url}. Status code: {response.status_code}"
            )
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

    for node in v2ray_nodes:
        if node.startswith("vmess://"):
            raw_data = base64.b64decode(node[8:])
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

                if not host and contains_letters(server):
                    host = server
                elif "." not in host:
                    invalid_host.append(host)
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
                    "network": node_json.get("net", "tcp"),
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

    print(
        f"Invalid_host: {len(invalid_host)}, Invalid_node: {len(invalid_node)}, Inactive online proxies: {len(inactive_online_proxies)}"
    )
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
        print(f"No data to save for {file_path}")
        return

    try:
        with open(file_path, "w") as file:
            yaml.dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=True,
            )
            print(f"Configuration has been written to {file_path}")
    except Exception as e:
        print(f"Error saving YAML file {file_path}: {e}")
        sys.exit(1)


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


def main(log_path=None):
    urls = [
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/resasanian/Mirza/main/vmess",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity"
    ]

    # "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/splitted/vmess.txt",
    # Extract inactive proxies from log file if provided
    inactive_proxies = extract_inactive_proxies(log_path) if log_path else []

    for url in urls:
        print(f"\n> Processing {url}")
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

    parser = argparse.ArgumentParser(
        description="Process V2Ray URLs and convert to Clash format."
    )
    parser.add_argument(
        "--log",
        type=str,
        help="Path to the log file containing inactive proxies (optional)",
    )

    args = parser.parse_args()

    log_file_path = args.log if args.log else None
    main(log_file_path)
