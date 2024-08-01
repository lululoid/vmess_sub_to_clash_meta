import base64
import json
import os
import re
import socket
import sys

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
        if response.status_code == 200:
            decoded_data = base64.b64decode(response.text).decode("utf-8")
            return decoded_data
        else:
            raise Exception(
                f"Failed to fetch V2Ray subscription from {url}. Status code: {response.status_code}"
            )
    except requests.exceptions.SSLError as e:
        print(
            f"SSL error occurred while fetching V2Ray subscription from {url}: {e}")
        print("Check your internet connection\n")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(
            f"An error occurred while fetching V2Ray subscription from {url}: {e}")
        sys.exit(1)


def convert_v2ray_to_clash(decoded_data):
    v2ray_nodes = decoded_data.strip().split("\n")
    clash_config = {"proxies": []}

    for node in v2ray_nodes:
        if node.startswith("vmess://"):
            node_data = base64.b64decode(node[8:]).decode("utf-8")
            try:
                node_json = json.loads(node_data)
                server = node_json.get("add", "unknown")
                port = int(node_json.get("port", 443))
                host = node_json.get("host", "")
                if contains_letters(server) and not host:
                    host = server
                servername = host

                clash_node = {
                    "name": node_json.get("ps", "Unnamed"),
                    "server": server,
                    "port": port,
                    "type": node[:5],
                    "uuid": node_json.get("id", ""),
                    "alterId": int(node_json.get("aid", 0)),
                    "cipher": node_json.get("cipher", "auto"),
                    "tls": node_json.get("tls", "") == "tls",
                    "skip-cert-verify": node_json.get("skip-cert-verify", True),
                    "servername": servername,
                    "network": node_json.get("net", "tcp"),
                    "ws-opts": {
                        "path": node_json.get("path", "/"),
                        "headers": {"Host": host},
                    },
                }
                clash_config["proxies"].append(clash_node)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {node_data}")
            except KeyError as e:
                print(f"Missing key {e} in node: {node_data}")

    return clash_config


def filter_proxies_by_port(config, port):
    filtered_proxies = [
        proxy for proxy in config["proxies"] if proxy.get("port") == port
    ]
    return {"proxies": filtered_proxies}


def update_server(config, new_server):
    for proxy in config["proxies"]:
        proxy["server"] = new_server
    return config


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


def compare_proxies(new_config, existing_config):
    new_proxies = {json.dumps(proxy, sort_keys=True)
                   for proxy in new_config["proxies"]}
    existing_proxies = {
        json.dumps(proxy, sort_keys=True) for proxy in existing_config["proxies"]
    }

    added_proxies = new_proxies - existing_proxies
    if added_proxies:
        print("New proxies found:")
        for proxy in added_proxies:
            print(json.loads(proxy))
        return True

    print("No update available")
    return False


def get_base_filename(url):
    path_parts = url.replace("https://", "").replace("http://", "").split("/")
    if len(path_parts) >= 3:
        return f"{path_parts[1]}_{path_parts[2]}"
    else:
        raise ValueError(
            "URL does not contain enough parts to extract base filename")


def main():
    urls = [
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/resasanian/Mirza/main/vmess",
    ]

    for url in urls:
        decoded_data = decode_v2ray_subscription(url)
        if decoded_data is None:
            continue

        clash_config = convert_v2ray_to_clash(decoded_data)

        try:
            filename_base = get_base_filename(url)
        except ValueError as e:
            print(f"Skipping URL {url}: {e}")
            continue

        # Load existing proxies
        existing_proxies = load_existing_proxies(
            f"{filename_base}_proxies.yaml")

        # Check for updates
        if existing_proxies:
            if not compare_proxies(clash_config, existing_proxies):
                continue

        # Save all proxies
        save_yaml(f"{filename_base}_proxies.yaml", clash_config)

        # Filter and save proxies with port 80
        proxies_port_80 = filter_proxies_by_port(clash_config, 80)
        save_yaml(f"{filename_base}_proxies_port_80.yaml", proxies_port_80)

        # Filter and save proxies with port 443
        proxies_port_443 = filter_proxies_by_port(clash_config, 443)
        save_yaml(f"{filename_base}_proxies_port_443.yaml", proxies_port_443)

        # Update server address and save
        new_server = "104.26.6.171"  # Replace with the new server IP or hostname
        updated_config_80 = update_server(proxies_port_80, new_server)
        save_yaml(f"{filename_base}_proxies_updated_80.yaml",
                  updated_config_80)

        updated_config_443 = update_server(proxies_port_443, new_server)
        save_yaml(f"{filename_base}_proxies_updated_443.yaml",
                  updated_config_443)


if __name__ == "__main__":
    main()
