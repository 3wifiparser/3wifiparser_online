import aiohttp
import asyncio
import json
import threading
import sqlite3
import cloud
import random
import shutil
import tqdm
import time
import sys
import config
import fw_parser

#temp database
rand_database_id = random.getrandbits(16)
shutil.copy("clean_base.db", f"temp{rand_database_id}.db")
db = sqlite3.connect(f"temp{rand_database_id}.db", check_same_thread=False)

map_end = False
db_lock = threading.Lock()
protocol = "https" if config.use_https else "http"
cur_progress = 0
headers = { 
  "Content-type": "application/json",  
  "Accept": "text/plain", 
  "Host": "3wifi.stascorp.com" 
}
ajax_apikey = "23ZRA8UBSLsdhbdJMp7IpbbsrDFDLuBC"

async def load(session: aiohttp.ClientSession, tile1, tile2, zoom, random_subtask=0, rescan_level=0, tqdm_bar: tqdm.tqdm=None):
    if rescan_level > 8 and config.limit_rescans:
        return {"ok": False, "desc": "Too many rescans"}
    try:
        r = await session.get(f"{protocol}://134.0.119.34/3wifi.php?a=map&scat=1&tileNumber={tile1},{tile2}&zoom={zoom}", headers=headers)
    except:
        await asyncio.sleep(2)
        return await load(session, tile1, tile2, zoom, random_subtask=random_subtask, rescan_level=rescan_level + 1, tqdm_bar=tqdm_bar)
    to_parse = await r.text()

    parsing_result = fw_parser.parse_map(to_parse)
    if not(parsing_result["ok"]):
        if tqdm_bar == None:
            print(parsing_result["desc"])
        else:
            tqdm_bar.write(parsing_result["desc"])
        if parsing_result["rescan"]:
            await asyncio.sleep(0.5)
            return await load(session, tile1, tile2, zoom, random_subtask=random_subtask, rescan_level=rescan_level + 1, tqdm_bar=tqdm_bar)
        else:
            return {"ok": False, "desc": parsing_result["desc"]}
    cur = db.cursor()
    try:
        cur.executemany(f"INSERT INTO networks (SSID, BSSID, lat, lon, rawmap_id) VALUES ((?),(?),(?),(?),{random_subtask})", parsing_result["result"])
        db.commit()
    except Exception as e:
        print("DB map scan err: " + str(e))
    cur.close()
    return {"ok": True, "nets": len(parsing_result["result"])}

async def scan_from_server():
    global cur_progress, random_subtask_id, map_end
    if config.scan_passwords:
        start_passwords_scan()
    print("Receiving a task from the server...")
    task = await cloud.get_free_task()
    private = False
    print("Privating task...")
    for i in range(5):
        if task.get("ok"):
            task = task["data"]
            min_maxTileX = json.loads(task["min_maxTileX"])
            min_maxTileY = json.loads(task["min_maxTileY"])
            progress = json.loads(task["min_max_progress"])
            privateresult = await cloud.private_task(task["id"])
            if privateresult.get("ok") == True:
                private = True
                break
            elif privateresult.get("desc") == "task privated":
                task = await cloud.get_free_task()
        else:
            if task.get("desc") == "no more tasks":
                time.sleep(60)
                return
            print("Error get task from server")
    if not(private):
        raise Exception("SERVER ERROR")
    print("Task privated")
    last_ping_time = time.time()
    tiles_cnt = (min_maxTileX[1] - min_maxTileX[0] + 1) * (min_maxTileY[1] - min_maxTileY[0] + 1)
    print(f"Need to scan {progress[1] - progress[0]} tiles")
    progressbar = tqdm.tqdm(total=(progress[1] - progress[0] + 1), ascii=True)
    random_subtask_id = random.getrandbits(32)
    total_found = 0
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(force_close=True, ssl=False)) as session:
        tasks = []
        tile1 = None
        prog_cnt = 0
        for x in range(min_maxTileX[0], min_maxTileX[1] + 1):
            if prog_cnt > progress[1]:
                break
            for y in range(min_maxTileY[0], min_maxTileY[1] + 1):
                if prog_cnt < progress[0]:
                    prog_cnt += 1
                    continue
                if prog_cnt > progress[1]:
                    break
                if tile1 == None:
                    tile1 = f"{x},{y}"
                    progressbar.update(1)
                    prog_cnt += 1
                    continue
                try:
                    tasks.append(asyncio.create_task(load(session, tile1, f"{x},{y}", 17, random_subtask=random_subtask_id, tqdm_bar=progressbar)))
                    tile1 = None
                    if len(tasks) >= config.map_async_level:
                        if time.time() - last_ping_time > 10: # ping task
                            tasks.append(asyncio.create_task(cloud.ping_task(task["id"], cur_progress)))
                            last_ping_time = time.time()
                        responses = await asyncio.gather(*tasks)
                        for resp in responses:
                            if resp["ok"] and "nets" in resp:
                                total_found += int(resp.get("nets"))
                            elif not(resp["ok"]):
                                progressbar.write("Function load() error: " + str(resp.get("desc")))
                        tasks.clear()
                except Exception as e:
                    print("######### " + str(e))
                prog_cnt += 1
                progressbar.update(1)
                progressbar.set_postfix_str(f"{total_found} networks found")
                cur_progress = prog_cnt
    map_end = True
    progressbar.close()
    cnter = 0
    sys.stdout.write("Loading passwords ")
    if config.scan_passwords:
        global passwd_threads, thread_tasks
        alive = True
        while alive:
            alive = False
            for i in passwd_threads:
                if i.is_alive():
                    alive = True
            if cnter > 100:
                await cloud.ping_task(task["id"], cur_progress)
                cnter = 0
            for cursor in '|/-\\':
                sys.stdout.write(cursor)
                sys.stdout.flush()
                sys.stdout.write("\b")
                time.sleep(0.1)
            cnter += 4
        thread_tasks.clear()
        passwd_threads.clear()
    map_end = False
    print("\nSending scan results to server")
    await load_task_to_server(random_subtask_id, task["id"])
    print("Completed!")

thread_tasks = []
passwd_threads = []

async def get_passwords(session, bssids: list):
    tasks = [asyncio.create_task(session.get(f"{protocol}://134.0.119.34/api/ajax.php?Version=0.51&Key={ajax_apikey}&Query=Find&BSSID={i}", headers=headers)) for i in bssids]
    responses = await asyncio.gather(*tasks)
    cnt = 0
    cur = db.cursor()
    to_base = []
    for resp in responses:
        to_base.append((await resp.text(), bssids[cnt]))
        cnt += 1
    try:
        with db_lock:
            cur.executemany("UPDATE networks SET API_ANS=(?) WHERE bssid=(?)", to_base)
            cur.close()
            bssids.clear()
            db.commit()
    except Exception as e:
        print("api_ans upd erorr: " + str(e))
        pass

def thread_balancer(threads_cnt, async_limit=8):
    all_queued = []
    for i in range(threads_cnt):
        for y in thread_tasks[i]:
            all_queued.append(y)
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT bssid FROM networks WHERE API_ANS IS NULL AND bssid NOT in (?) LIMIT (?)", (str(all_queued)[1:-1], int(async_limit) * threads_cnt))
    bssids = cursor.fetchall()
    cursor.close()
    thread_tasks_cnt = []
    for i in range(threads_cnt):
        thread_tasks_cnt.append(len(thread_tasks[i]))
    for i in bssids:
        min_load_ind = 0
        for y in range(len(thread_tasks_cnt)):
            if thread_tasks_cnt[y] < thread_tasks_cnt[min_load_ind]:
                min_load_ind = y
        if thread_tasks_cnt[min_load_ind] < async_limit:
            thread_tasks[min_load_ind].append(i[0])
            thread_tasks_cnt[min_load_ind] += 1

async def pool_passwords(thread_ind=0, async_limit=8):
    global map_end
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(force_close=True, ssl=False)) as session:
        while not(map_end) or len(thread_tasks[thread_ind]) > 0:
            try:
                if len(thread_tasks[thread_ind]) > 0:
                    if len(thread_tasks[thread_ind]) < async_limit:
                        with db_lock:
                            thread_balancer(config.pass_threads_cnt, async_limit)
                    await get_passwords(session, thread_tasks[thread_ind])
                    with db_lock:
                        thread_balancer(config.pass_threads_cnt, async_limit)
                else:
                    with db_lock:
                        thread_balancer(config.pass_threads_cnt, async_limit)
                    await asyncio.sleep(0.5)
            except Exception as e:
                print("pool " + str(e))

def start_passwords_scan():
    global passwd_threads
    for i in range(config.pass_threads_cnt):
        thread_tasks.append([])
    thread_balancer(config.pass_threads_cnt, config.pass_async_level)
    for i in range(config.pass_threads_cnt):
        th = threading.Thread(target=asyncio.run, name=f"3wifiparser{i}", args=(pool_passwords(i, config.pass_async_level), ))
        passwd_threads.append(th)
        th.start()

async def load_task_to_server(random_subtask_id, server_task_id):
    cur = db.cursor()
    cur.execute("SELECT SSID,BSSID,API_ANS,lat,lon FROM networks WHERE rawmap_id=?", (random_subtask_id, ))
    data = cur.fetchall()
    parsed_data = []
    for i in data:
        psd = [i[0], i[1], None, None, i[3], i[4]]
        if i[2] == None:
            parsed_data.append(psd)
            continue
        api_ans = json.loads(i[2])
        if not(api_ans["Successes"]):
            parsed_data.append(psd)
            continue
        psd[2] = ",".join(api_ans["Keys"])
        psd[3] = ",".join(api_ans["WPS"])
        parsed_data.append(psd)
    ans = await cloud.complete_task(parsed_data, server_task_id)
    if not(ans.get("ok")):
        if ans.get("desc") == "task is free":
            print("###TASK IS FREE###")
            reprivate = await cloud.private_task(server_task_id)
            if not(reprivate.get("ok")):
                print("### REPRIVATE ERROR ###")
                return
            ans = await cloud.complete_task(parsed_data, server_task_id)
            if not(ans.get("ok")):
                print("### RECOMPLETE FAILURE ###")

async def pool_from_server():
        while True:
            try:
                await scan_from_server()
            except Exception as e:
                print(f"EXCEPTION {e}")
                time.sleep(2)

if __name__ == "__main__":
    asyncio.run(pool_from_server())
    print("End")