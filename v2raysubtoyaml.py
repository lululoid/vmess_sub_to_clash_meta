import base64
import json
import requests
import yaml

def decode_v2ray_subscription(url):
    response = requests.get(url)
    if response.status_code == 200:
        try:
            decoded_data = base64.b64decode(response.text).decode('utf-8')
            return decoded_data 
        except requests.exceptions.SSLError:
            print("Connection Error")
    else:
        raise Exception(f"Failed to fetch V2Ray subscription from {url}. Status code: {response.status_code}")

def convert_v2ray_to_clash(decoded_data):
    v2ray_nodes = decoded_data.strip().split('\n')
    clash_config = {
        'proxies': []
    }
    
    for node in v2ray_nodes:
        if node.startswith('vmess://'):
            node_data = base64.b64decode(node[8:]).decode('utf-8')
            try:
                node_json = json.loads(node_data)
                
                clash_node = {
                    'name': node_json.get('ps', 'Unnamed'),
                    'server': node_json.get('add', 'unknown'),
                    'port': int(node_json.get('port', 443)),
                    'type': node[:5],
                    'uuid': node_json.get('id', ''),
                    'alterId': int(node_json.get('aid', 0)),
                    'cipher': node_json.get('cipher', 'auto'),
                    'tls': node_json.get('tls', '') == 'tls',
                    'skip-cert-verify': node_json.get('skip-cert-verify', True),
                    'network': node_json.get('net', 'tcp'),
                    'ws-opts': {
                        'path': node_json.get('path', '/'),
                        'headers': {'Host': node_json.get('host', '')}
                    }
                }
                clash_config['proxies'].append(clash_node)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {node_data}")
            except KeyError as e:
                print(f"Missing key {e} in node: {node_data}")
    
    return clash_config

def filter_proxies_by_port(config, port):
    filtered_proxies = [proxy for proxy in config['proxies'] if proxy.get('port') == port]
    return {'proxies': filtered_proxies}

def update_server(config, new_server):
    for proxy in config['proxies']:
        proxy['server'] = new_server
    return config

def save_yaml(filename, data):
    yaml_str = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)
    
    # Split the YAML string into lines
    lines = yaml_str.split('\n')
    
    # Adjust indentation
    modified_lines = []
    for line in lines:
        if line.startswith('proxies:'):
            # Do not add extra indentation to the 'proxies:' line
            modified_lines.append(line)
        elif line:
            # Add 2 spaces for indentation to all other lines
            modified_lines.append('  ' + line)
    
    yaml_str_with_spaces = '\n'.join(modified_lines)
    
    with open(filename, 'w') as file:
        file.write(yaml_str_with_spaces)
    print(f"Configuration has been written to {filename}")

def main():
    v2ray_subscription_url = 'https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt'
    decoded_data = decode_v2ray_subscription(v2ray_subscription_url)
    clash_config = convert_v2ray_to_clash(decoded_data)
    
    # Save all proxies
    save_yaml('proxies.yaml', clash_config)
    
    # Filter and save proxies with port 80
    proxies_port_80 = filter_proxies_by_port(clash_config, 80)
    save_yaml('proxies_port_80.yaml', proxies_port_80)
    proxies_port_443 = filter_proxies_by_port(clash_config, 443)
    save_yaml('proxies_port_443', proxies_port_443)
    # Update server address and save
    new_server = '104.26.6.171'  # Replace with the new server IP or hostname
    updated_config_80 = update_server(proxies_port_80, new_server)
    save_yaml('proxies_updated_80.yaml', updated_config_80)
    updated_config_443 = update_server(proxies_port_443, new_server)
    save_yaml('proxies_updated_443.yaml', updated_config_443)

if __name__ == '__main__':
    main()
