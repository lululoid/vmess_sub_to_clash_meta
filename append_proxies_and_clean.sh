#!/system/bin/sh
if [ $# -eq 0 ] || [ "$1" = "-h" ]; then
	cat <<EOF
Usage: ./append_proxies_and_clean.sh <proxies provider file> <log_file [optional]>
	-h | Show this message
EOF
	exit 1
fi

proxies_dir="$2"
if [ -n "$proxies_dir" ]; then
	log_file=$(ls -tr "$proxies_dir"/*.log | tail -n1)
else
	echo "! Please provide log_file or directory for the logs
	"
fi

if [ -n "$log_file" ]; then
	:
else
	echo "> Provide log from clash in debug level in mihomo to clean dead proxies
	"
fi

echo "> Loading environment
"
source ./sniffing_tools_env/bin/activate
echo "> Generating proxy_providers from subcription
"
python ./v2raysubtoyaml.py

for proxy in ./proxies/*/proxies_updated_80.yaml; do
	echo "> Appending $proxy to $1
	"
	echo "> Cleaning dead proxies if any
"
	if [ -n "$log_file" ]; then
		python ./clean_proxy_provider.py "$proxy" "$log_file"
	else
		python ./clean_proxy_provider.py "$proxy"
	fi

	python append_proxies.py $proxy "$1"
done
