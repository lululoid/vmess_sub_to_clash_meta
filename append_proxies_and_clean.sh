#!/system/bin/sh

# Show usage if no arguments are provided or help flag is used
if [ $# -eq 0 ] || [ "$1" = "-h" ]; then
	cat <<EOF
Usage: ./append_proxies_and_clean.sh <proxies provider file> [log_file or log_directory (optional)]
	-h | Show this message
EOF
	exit 1
fi

proxies_file="$1"
log_source="$2" # log_file or directory for logs

# Check if the second argument is a directory or file
if [ -d "$log_source" ]; then
	# Find up to 5 most recent log files in the directory
	log_files=$(ls -tr "$log_source"/*.log | tail -n8)
elif [ -f "$log_source" ]; then
	# If it's a file, use it as log_file
	log_files="$log_source"
else
	# No log source provided or invalid log source
	echo "! Please provide a valid log file or directory containing logs"
	log_files=""
fi

if [ -n "$log_files" ]; then
	echo "Using log files from:"
	for log_file in $log_files; do
		echo "  $log_file"
	done
else
	echo "> No log file provided. Cleaning dead proxies will be skipped."
fi

echo "> Loading environment..."
source ./sniffing_tools_env/bin/activate

echo "> Generating proxy providers from subscription..."
# Call Python script with or without log file
if [ -n "$log_files" ]; then
	for log_file in $log_files; do
		python ./v2raysubtoyaml.py --log "$log_file"
	done
else
	python ./v2raysubtoyaml.py
fi

# Loop through and append proxies
for proxy in ./proxies/*/updated_port.yaml; do
	echo "> Appending $proxy to $proxies_file..."
	python append_proxies.py "$proxy" "$proxies_file"
done

# Clean proxies with each log file
if [ -n "$log_files" ]; then
	IFS=$'\n'
	for log_file in $log_files; do
		echo "Using $log_file for cleaning"
		python ./clean_proxy_provider.py "$1" "$log_file"
	done
else
	python ./clean_proxy_provider.py "$1"
fi
