import os.path
from io import BytesIO
import json
import datetime as dt
from zipfile import ZipFile
from string import ascii_lowercase
from dateutil.parser import isoparse
import requests
import pprint

CACHE_URL_BASE = "https://archive.openrs2.org"
UTC = dt.timezone.utc


def make_output_folder(date_str: str, sub_ver: int, working_dir: str) -> str:
    version_count = 0
    letter = "a"
    out_folder = os.path.join(working_dir, f"{date_str}_{sub_ver}_{letter}")
    while os.path.exists(out_folder):
        version_count += 1
        letter = ascii_lowercase[version_count]
        out_folder = os.path.join(working_dir, f"{date_str}_{sub_ver}_{letter}")

    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
    return out_folder


def get_cache_info(version=None) -> tuple[int, str]:
    if not version:
        # Fetch the latest cache
        cache_id, date_str, sub_ver = get_latest_cache()
    else:
        # Fetch a specific cache, passed as an arg
        # Arg should be of format {year}-{month}-{day}_{alphanum}
        date, num = version.split("_")
        cache_id, date_str, sub_ver = get_specific_cache(date, num)
    print(f"Found cache {cache_id} from {date_str}\n")
    return cache_id, date_str, sub_ver


def get_specific_cache(date, num) -> tuple[int, str]:
    year, month, day = map(int, date.split("-"))
    num = int(num)
    targetDate = dt.date(year, month, day)
    cache_list = requests.get(CACHE_URL_BASE + "/caches.json", timeout=15).json()
    cachesOnSameDay = find_caches_on_date(targetDate, cache_list)
    timeOptions = sorted(list(cachesOnSameDay.keys()))
    try:
        requestedTime = timeOptions[num]
        cache_id = cachesOnSameDay[requestedTime]["id"]
        date_str = requestedTime.strftime("%Y-%m-%d")
        return cache_id, date_str, num
    except IndexError:
        raise IndexError(f"Could not find cache number {num} on {targetDate}.\n"
                         f"Try another date or cache number.")


def find_caches_on_date(targetDate, cache_list):
    cache_list.append({
            "timestamp": dt.datetime(2024, 5, 29, 15, 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "id": 11111111111,
            "scope": "runescape",
            "game": "oldschool",
            "environment": "live"
        })

    cacheTimeMap = dict()
    for cache in cache_list:
        # Cache must be of the correct type
        if (cache["scope"] != "runescape" 
                or cache["game"] != "oldschool" 
                or cache["environment"] != "live"):
            continue

        # Map timestamps to caches
        timestamp = cache["timestamp"]
        if not timestamp:
            continue
        timestamp = isoparse(timestamp)
        cacheTimeMap[timestamp] = cache

    def sameDate(targetDate: dt.datetime, itemToCheck: dt.datetime):
        return targetDate == itemToCheck.date()

    # Filter the dict to only entries that fall on the same day
    cachesOnSameDay = {timestamp: cache for timestamp, cache 
                       in cacheTimeMap.items() 
                       if sameDate(targetDate, timestamp)}
    return cachesOnSameDay


def get_latest_cache() -> tuple[int, str]:
    cache_list = requests.get(CACHE_URL_BASE + "/caches.json", timeout=15).json()
    latest = dt.datetime(1970, 1, 1, tzinfo=UTC)
    cache_id = -1
    for cache in cache_list:
        if (cache["scope"] != "runescape" 
                or cache["game"] != "oldschool" 
                or cache["environment"] != "live"):
            continue

        timestamp = cache["timestamp"]
        if not timestamp:
            continue

        date = isoparse(timestamp)
        if date > latest:
            latest = date
            cache_id = cache["id"]

    cachesOnSameDay = find_caches_on_date(latest.date(), cache_list)
    timeOptions = sorted(list(cachesOnSameDay.keys()))
    sub_ver = len(timeOptions)-1

    date_str = latest.strftime("%Y-%m-%d")
    return cache_id, date_str, sub_ver


def download_xteas(cache_id, out_folder):
    keys_path = os.path.join(out_folder, "xteas.json")

    print("Downloading xteas...")
    start = dt.datetime.now()
    response = requests.get(CACHE_URL_BASE + f"/caches/runescape/{cache_id}/keys.json", timeout=30)
    end = dt.datetime.now()
    print(f"{int((end-start).total_seconds())}s elapsed.\n")

    key_list = []
    for xtea in response.json():
        new_key = {}
        for key, val in xtea.items():
            # Runelite expects region/keys, openrs2 provides mapsquare/key
            if key == "mapsquare":
                new_key["region"] = val
            elif key == "key":
                new_key["keys"] = val

        key_list.append(new_key)

    with open(keys_path, "w", encoding="utf-8") as file:
        json.dump(key_list, file)


def download_cache(cache_id, out_folder):
    print("Downloading cache...")
    start = dt.datetime.now()
    raw = requests.get(CACHE_URL_BASE + f"/caches/runescape/{cache_id}/disk.zip", timeout=60).content
    end = dt.datetime.now()
    print(f"{int((end-start).total_seconds())}s elapsed.\n")

    z = ZipFile(BytesIO(raw))
    z.extractall(out_folder)


def download(working_dir, version=None):
    cache_id, date_str, sub_ver = get_cache_info(version)
    out_folder = make_output_folder(date_str, sub_ver, working_dir)

    download_xteas(cache_id, out_folder)
    download_cache(cache_id, out_folder)

    return out_folder

if __name__ == "__main__":
    download("osrs-wiki-maps/out/mapgen/versions", "2024-05-29_0")