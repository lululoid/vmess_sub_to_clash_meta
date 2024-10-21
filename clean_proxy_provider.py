import difflib
import os
import re
import socket
import sys

import emoji
import geoip2.database
import IP2Location
import pycountry
import requests
import yaml

dead_proxies = []
database = IP2Location.IP2Location(
    os.path.join(os.getcwd(), "IP2LOCATION-LITE-DB1.BIN")
)
# Get all available emoji aliases
emoji_data = emoji.EMOJI_DATA


def generate_country_codes_and_names():
    country_data = {}

    for country in pycountry.countries:
        # Get the alpha_2 code and country name
        country_code = country.alpha_2  # ISO 3166-1 alpha-2 code
        country_name = country.name
        country_data[country_code] = country_name

    return country_data


def generate_country_flags():
    # Unicode range for regional indicator symbols
    base = 0x1F1E6  # Regional indicator symbol letter A
    flags = []

    # Loop through the letters A-Z (26 letters)
    for i in range(26):
        for j in range(26):
            # Create a flag by combining two regional indicators
            flag = chr(base + i) + chr(base + j)
            flags.append(flag)

    return flags


# Generate the list of country codes and names
country_flags = generate_country_flags()
country_codes_and_names = generate_country_codes_and_names()


# A function to get the flag emoji from a country name
def get_flag_emoji(country_name):
    # The word you want to match
    search_term = country_name

    # Collect all possible names (from 'en' and 'alias') for comparison
    emoji_names = []
    for emoji, details in emoji_data.items():
        emoji_names.append(details["en"])  # Add the main 'en' key
        emoji_names.extend(details.get("alias", []))  # Add aliases if present

    # Find the closest match using difflib
    closest_match = difflib.get_close_matches(search_term, emoji_names, n=1)

    # Find the emoji that corresponds to the closest match
    if closest_match:
        match = closest_match[0]
        for emoji, details in emoji_data.items():
            if details["en"] == match or match in details.get("alias", []):
                return emoji
    else:
        return "🏳️"  # Return default flag in case of any exception


def get_ip_address(hostname):
    try:
        print(f"> Trying to get ip address of {hostname}")
        # Resolve the hostname to an IP address
        ip_address = socket.gethostbyname(hostname)
        print(f"The ip address is {ip_address}")
        return ip_address
    except socket.gaierror:
        print(f"Error: Unable to resolve hostname '{hostname}'")
        return None


def get_location(ip_address):
    try:
        reader = geoip2.database.Reader("GeoLite2-Country.mmdb")
        response = reader.country(ip_address)  # Example IP
        rec = database.get_all(ip_address)

        if response.country.name:
            return response.country.name
        elif rec.country_long:
            return rec.country_long
        else:
            print("Error fetching location data.")
            return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


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
            # Process lines in reverse order to make sure it starts from the most recent test first
            for line in reversed(lines):
                if alive_status_pattern.search(line):
                    match = uid_pattern.search(line)
                    if match:
                        uid = match.group(1)
                        # Extracting proxy name from the line
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
            dead_proxies.append(proxy_name)
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

    print(f"{len(dead_proxies)} is removed")
    return {"proxies": cleaned_proxies}


def add_location_emoji(proxies_data):
    proxies = []
    for proxy in proxies_data["proxies"]:
        host = proxy.get("ws-opts", {}).get("headers", {}).get("Host")
        proxy_name = proxy.get("name")  # Use .get() to avoid KeyError
        ip_address = get_ip_address(host)

        if ip_address:
            location_info = get_location(ip_address)

            if location_info:
                # Replace spaces with underscores in the country name
                country_name = location_info.replace(" ", "_")

                # Add the flag emoji to the proxy name
                flag_emoji = get_flag_emoji(country_name)
                print(
                    f"> {proxy_name} is detected from {country_name}({flag_emoji})\n")

                # Print the list
                for country_code, country_name in country_codes_and_names.items():
                    # Check if the flag emoji is already in the proxy name
                    if (
                        flag_emoji not in proxy_name
                        and country_code not in proxy_name
                        and country_name not in proxy_name
                    ):
                        proxy_name = f"{flag_emoji} {proxy_name}"
                        # Update the proxy dictionary with the new proxy name
                        proxy["name"] = proxy_name

            # Append the updated proxy to the proxies list
            proxies.append(proxy)
        else:
            dead_proxies.append(proxy)

    return {"proxies": proxies}


def main(proxies_path, log_path=None):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    cleaned_proxies_data = clean_proxies(proxies_data["proxies"])
    cleaned_proxies_data_length = len(proxies_data["proxies"])
    try:
        user_input = input(
            f"Proxies is {cleaned_proxies_data_length}, you sure want to continue? \nPress enter to continue or Ctrl+C to skip..."
        )
        final_data = add_location_emoji(cleaned_proxies_data)
    except KeyboardInterrupt:
        print("\nCtrl+C detected! Skipping...")
        final_data = cleaned_proxies_data

    print(f"Number of dead proxies: {len(dead_proxies)}")
    save_yaml(proxies_path, final_data)

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
