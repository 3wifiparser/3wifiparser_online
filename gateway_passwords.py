import aiohttp
import database
import asyncio
import threading
import json

api_url = "https://wifibase.zapto.org:7080/api"
api_key = "23ZRA8UBSLsdhbdJMp7IpbbsrDFDLuBC"
thread = None
map_end = False

headers = {
    "Content-type": "application/json", 
    "Accept": "text/plain"
}


if not(api_url.endswith("/")):
    api_url += "/"
api_url += "apiquery"

async def get_passwords(bssids: list, session):
    data = {"key": api_key, "bssid": [i[0] for i in bssids]}
    resp = await session.post(api_url, data=json.dumps(data), headers=headers)
    resp = await resp.json()
    if resp["result"]:
      database.save_passwords_gate(resp["data"])
      return {"ok": True}
    elif resp["error"] == "cooldown":
        await asyncio.sleep(10)
        return get_passwords(bssids)
    elif resp["error"] == "request failed":
          await asyncio.sleep(3)
          return get_passwords(bssids)
    else:
        return {"ok": False}
    
async def pool_passwords():
    global map_end
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                if map_end:
                    if database.get_cnt_null_pass() < 1:
                        break
                bssids = database.get_null_passwords_bssids(100)
                if len(bssids) == 0:
                    await asyncio.sleep(0.5)
                    continue
                result = await get_passwords(bssids, session)
                if not(result["ok"]):
                    print("Pass get err")
            except Exception as e:
                print("pool " + str(e))
    
def start_passwords_scan():
    global thread
    thread = threading.Thread(target=asyncio.run, name=f"passpool", args=(pool_passwords(), ))
    thread.start()


def is_pooling():
    global thread
    return thread.is_alive()

def clear():
    global map_end
    map_end = False

def join():
    global thread
    thread.join()