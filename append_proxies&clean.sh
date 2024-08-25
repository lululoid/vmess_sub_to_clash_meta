#!/system/bin/sh
if [ $# -eq 0 ]; then
	echo "Please provide the proxy that is gonna get updated"
	exit 1
fi

proxies_dir="$HOME/Clash config"
log_file=$(ls -tr "$proxies_dir"/*.log | tail -n1)

if [ -n "$log_file" ]; then
	:
else
	echo "Log isn't exist"
	exit 1
fi

source ./sniffing_tools_env/bin/activate
python ./v2raysubtoyaml.py

for proxy in ./proxies/*/proxies_updated_80.yaml; do
	python append_proxies.py $proxy "$1"
done

python ./clean_proxy_provider.py "$1" "$log_file"
