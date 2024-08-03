import yaml
import socket
import sys

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

def test_server(server, port, timeout=5):
    try:
        with socket.create_connection((server, port), timeout) as sock:
            return True
    except (socket.timeout, socket.error):
        return False

def main(proxies_path):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    proxies = proxies_data["proxies"]
    results = []

    for proxy in proxies:
        server = proxy.get("server")
        port = proxy.get("port")
        if server and port:
            is_reachable = test_server(server, port)
            results.append((server, port, is_reachable))
        else:
            print(f"Invalid proxy configuration: {proxy}")

    print("\nServer Test Results:")
    for server, port, is_reachable in results:
        status = "Reachable" if is_reachable else "Unreachable"
        print(f"Server: {server}, Port: {port} - {status}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_servers.py <proxies.yaml>")
        sys.exit(1)

    proxies_path = sys.argv[1]
    main(proxies_path)
