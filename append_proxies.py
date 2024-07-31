import sys
import yaml

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

def main(new_proxies_path, old_proxies_path):
    new_proxies = load_yaml(new_proxies_path)
    old_proxies = load_yaml(old_proxies_path)

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
