import os
import re
import socket
import sys

import emoji
import requests
import yaml

# List of known country names and their respective flags
country_to_code = {
    "Afghanistan": "AF",
    "Albania": "AL",
    "Algeria": "DZ",
    "Andorra": "AD",
    "Argentina": "AR",
    "Armenia": "AM",
    "Australia": "AU",
    "Austria": "AT",
    "Azerbaijan": "AZ",
    "Bahamas": "BS",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Barbados": "BB",
    "Belarus": "BY",
    "Belgium": "BE",
    "Belize": "BZ",
    "Benin": "BJ",
    "Bhutan": "BT",
    "Bolivia": "BO",
    "Bosnia and Herzegovina": "BA",
    "Botswana": "BW",
    "Brazil": "BR",
    "Brunei": "BN",
    "Bulgaria": "BG",
    "Burkina Faso": "BF",
    "Burundi": "BI",
    "Cambodia": "KH",
    "Cameroon": "CM",
    "Canada": "CA",
    "Cape Verde": "CV",
    "Central African Republic": "CF",
    "Chad": "TD",
    "Chile": "CL",
    "China": "CN",
    "Colombia": "CO",
    "Costa Rica": "CR",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Djibouti": "DJ",
    "Dominican Republic": "DO",
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "Estonia": "EE",
    "Eswatini": "SZ",
    "Ethiopia": "ET",
    "Finland": "FI",
    "France": "FR",
    "Gabon": "GA",
    "Georgia": "GE",
    "Germany": "DE",
    "Ghana": "GH",
    "Greece": "GR",
    "Grenada": "GD",
    "Guatemala": "GT",
    "Guinea": "GN",
    "Guinea-Bissau": "GW",
    "Guyana": "GY",
    "Haiti": "HT",
    "Honduras": "HN",
    "Hungary": "HU",
    "Iceland": "IS",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Iraq": "IQ",
    "Ireland": "IE",
    "Israel": "IL",
    "Italy": "IT",
    "Jamaica": "JM",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Laos": "LA",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Lesotho": "LS",
    "Liberia": "LR",
    "Libya": "LY",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Madagascar": "MG",
    "Malawi": "MW",
    "Malaysia": "MY",
    "Malta": "MT",
    "Mexico": "MX",
    "Moldova": "MD",
    "Monaco": "MC",
    "Mongolia": "MN",
    "Montenegro": "ME",
    "Morocco": "MA",
    "Mozambique": "MZ",
    "Myanmar": "MM",
    "Namibia": "NA",
    "Nepal": "NP",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Nicaragua": "NI",
    "Niger": "NE",
    "Nigeria": "NG",
    "North Macedonia": "MK",
    "Norway": "NO",
    "Oman": "OM",
    "Pakistan": "PK",
    "Panama": "PA",
    "Papua New Guinea": "PG",
    "Paraguay": "PY",
    "Peru": "PE",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Qatar": "QA",
    "Romania": "RO",
    "Russia": "RU",
    "Rwanda": "RW",
    "Saudi Arabia": "SA",
    "Senegal": "SN",
    "Serbia": "RS",
    "Singapore": "SG",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "South Africa": "ZA",
    "South Korea": "KR",
    "South Sudan": "SS",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Sudan": "SD",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Syria": "SY",
    "Taiwan": "TW",
    "Tajikistan": "TJ",
    "Tanzania": "TZ",
    "Thailand": "TH",
    "Togo": "TG",
    "Trinidad and Tobago": "TT",
    "Tunisia": "TN",
    "Turkey": "TR",
    "Turkmenistan": "TM",
    "Uganda": "UG",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "United States": "US",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
    "Venezuela": "VE",
    "Vietnam": "VN",
    "Yemen": "YE",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
}


def has_country_name_or_flag(proxy_name):
    # Check if the proxy name already contains a country name or flag emoji
    # Check for flag emojis
    for country_name, country_code in country_to_code.items():
        # Flag emoji format
        flag_emoji = emoji.emojize(f":{country_code.lower()}:")
        if flag_emoji in proxy_name or country_name in proxy_name:
            return True
    return False


# A function to get the flag emoji from a country name
def get_flag_emoji(country_name):
    try:
        # Get the country code
        country_code = country_to_code.get(country_name)

        if country_code:
            # Convert country code to the flag emoji using Unicode
            flag = emoji.emojize(f":{country_code.lower()}:")
            return flag
        else:
            print(f"Unknown country: {country_name}. Returning default flag.")
            return "🏳️"  # Default flag for unknown countries
    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error
        return "🏳️"  # Return default flag in case of any exception


def get_ip_address(hostname):
    try:
        # Resolve the hostname to an IP address
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror:
        print(f"Error: Unable to resolve hostname '{hostname}'")
        return None


def get_location(ip_address):
    try:
        # Use an API to get location data
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        data = response.json()
        if data["status"] == "success":
            return {
                "ip": data["query"],
                "country": data["country"],
                "region": data["regionName"],
                "city": data["city"],
                "zip": data["zip"],
                "lat": data["lat"],
                "lon": data["lon"],
            }
        else:
            print("Error fetching location data.")
            return None
    except requests.RequestException as e:
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
    dead_proxies = []

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

    print(f"Number of dead proxies: {len(dead_proxies)}")
    return {"proxies": cleaned_proxies}


def add_location_emoji(proxies_data):
    proxies = []
    num_proxies = len(proxies_data["proxies"])  # Get the number of proxies

    # Ask the user for confirmation if there are proxies
    if num_proxies == 0:
        print("No proxies found.")
        return {"proxies": []}  # Return empty list if no proxies

    print(f"Found {num_proxies} proxies.")
    input("Press Enter to continue...")  # Wait for user confirmation

    for proxy in proxies_data["proxies"]:
        host = proxy.get("ws-opts", {}).get("headers", {}).get("Host")
        proxy_name = proxy["name"]
        ip_address = get_ip_address(host)

        if ip_address:
            location_info = get_location(ip_address)

            if has_country_name_or_flag(proxy_name):
                print("Proxy name already contains a country name or flag emoji.")
            else:
                # Add the flag emoji to the proxy name
                flag_emoji = get_flag_emoji(location_info["country"])
                proxy_name = f"{flag_emoji} {proxy_name}"
                # Update the proxy dictionary with the new proxy name
                proxy["name"] = proxy_name

        # Append the updated proxy to the proxies list
        proxies.append(proxy)

    return {"proxies": proxies}


def main(proxies_path, log_path=None):
    proxies_data = load_yaml(proxies_path)

    if not proxies_data or "proxies" not in proxies_data:
        print("No proxies found in the provided YAML file.")
        return

    cleaned_proxies_data = clean_proxies(proxies_data["proxies"])
    final_data = add_location_emoji(cleaned_proxies_data)

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
