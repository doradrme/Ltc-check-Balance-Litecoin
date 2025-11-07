import requests
import threading
from concurrent.futures import ThreadPoolExecutor


PROXY = "http://user:pass@ip:port"
SOCHAIN_API_URL = "https://sochain.com/api/v2/get_address_balance/LTC/{}"
BLOCKCYPHER_API_URL = "https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
BLOCKCHAIR_API_URL = "https://api.blockchair.com/litecoin/dashboards/address/{address}?limit=0"
INPUT_FILE = "ltc.txt"
OUTPUT_FILE = "ltc_balances.txt"


def _get_json(url, proxy=None, timeout=10, retries=3):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, proxies=proxies, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            last_exc = e
        try:
            import time
            time.sleep(0.6 * (attempt + 1))
        except Exception:
            pass
    if last_exc:
        raise last_exc
    return None


def get_ltc_balance_sochain(address, proxy=None):
    try:
        url = SOCHAIN_API_URL.format(address)
        data = _get_json(url, proxy=proxy)
        if data and data.get("status") == "success" and "data" in data:
            confirmed = data["data"].get("confirmed_balance")
            if confirmed is not None:
                return float(confirmed)
        return f"Error: Unexpected response from SoChain"
    except Exception as e:
        return f"An error occurred (SoChain): {e}"


def get_ltc_balance_blockcypher(address, proxy=None):
    try:
        url = BLOCKCYPHER_API_URL.format(address=address)
        data = _get_json(url, proxy=proxy)
        if isinstance(data, dict) and "final_balance" in data:
            return int(data["final_balance"]) / 100_000_000
        return f"Error: Unexpected response from BlockCypher LTC"
    except Exception as e:
        return f"An error occurred (BlockCypher): {e}"


def get_ltc_balance_blockchair(address, proxy=None):
    try:
        url = BLOCKCHAIR_API_URL.format(address=address)
        data = _get_json(url, proxy=proxy)
        if data and isinstance(data, dict) and data.get("data") and address in data["data"]:
            info = data["data"][address]["address"]
            if "balance" in info:
                return int(info["balance"]) / 100_000_000
        return f"Error: Unexpected response from Blockchair"
    except Exception as e:
        return f"An error occurred (Blockchair): {e}"


def get_ltc_balance(address, proxy=None):
    result = get_ltc_balance_sochain(address, proxy=proxy)
    if isinstance(result, (int, float)):
        return result
    result2 = get_ltc_balance_blockchair(address, proxy=proxy)
    if isinstance(result2, (int, float)):
        return result2
    result3 = get_ltc_balance_blockcypher(address, proxy=proxy)
    return result3


def process_address(address, proxy, results_dict, lock):
    balance = get_ltc_balance(address, proxy=proxy)
    with lock:
        results_dict[address] = balance
        print(f"Address: {address}, Balance: {balance} LTC")


def check_balances_from_file(file_path, proxy=None, max_threads=50):
    try:
        with open(file_path, 'r') as file:
            addresses = [line.strip() for line in file if line.strip()]

        results = {}
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for address in addresses:
                executor.submit(process_address, address, proxy, results, lock)

        return results
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return {}


def save_balances_to_file(balances, output_path):
    try:
        with open(output_path, 'w') as file:
            saved_count = 0
            for address, balance in balances.items():
                if isinstance(balance, (int, float)) and balance > 0:
                    file.write(f"{address} => {balance} LTC\n")
                    saved_count += 1
            print(f"\n✅ Results saved to: {output_path}")
            print(f"📊 Saved {saved_count} addresses with balance out of {len(balances)} total addresses")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")


if __name__ == "__main__":
    balances = check_balances_from_file(INPUT_FILE, proxy=PROXY)
    save_balances_to_file(balances, OUTPUT_FILE)


