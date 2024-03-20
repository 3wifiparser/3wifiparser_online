import threading
import aiohttp
import database
import asyncio
import config
import logging

thread_tasks = []
passwd_threads = []

api_path = ""
ajax_apikey = ""
map_end = False
headers = { 
  "Content-type": "application/json",  
  "Accept": "text/plain", 
  "Host": "3wifi.stascorp.com" 
}
ajax_apikey = "23ZRA8UBSLsdhbdJMp7IpbbsrDFDLuBC"

def set_api_url(url):
    api_path = url

async def get_passwords(session, bssids: list):
    tasks = [asyncio.create_task(session.get(f"{api_path}/api/ajax.php?Version=0.51&Key={ajax_apikey}&Query=Find&BSSID={i}", headers=headers)) for i in bssids]
    responses = await asyncio.gather(*tasks)
    to_base = []
    for index, resp in enumerate(responses):
        to_base.append((await resp.json(), bssids[index]))
    database.save_passwords_ajax(to_base)

def thread_balancer(threads_cnt, async_limit=8):
    all_queued = []
    for i in range(threads_cnt):
        for y in thread_tasks[i]:
            all_queued.append(y)
    bssids = database.get_bssids_tb(all_queued, async_limit * threads_cnt - len(all_queued))
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
        while True:
            try:
                if map_end:
                    if database.get_cnt_null_pass() < 1:
                        break
                if len(thread_tasks[thread_ind]) > 0:
                    if len(thread_tasks[thread_ind]) < async_limit:
                        thread_balancer(config.pass_threads_cnt, async_limit)
                    await get_passwords(session, thread_tasks[thread_ind])
                    thread_tasks[thread_ind].clear()
                    thread_balancer(config.pass_threads_cnt, async_limit)
                else:
                    thread_balancer(config.pass_threads_cnt, async_limit)
                    await asyncio.sleep(0.5)
            except Exception:
                logging.exception("ajax.pool_passwords while exception")

def start_passwords_scan():
    global passwd_threads
    for i in range(config.pass_threads_cnt):
        thread_tasks.append([])
    thread_balancer(config.pass_threads_cnt, config.pass_async_level)
    for i in range(config.pass_threads_cnt):
        th = threading.Thread(target=asyncio.run, name=f"3wifiparser{i}", args=(pool_passwords(i, config.pass_async_level), ))
        passwd_threads.append(th)
        th.start()

def is_pooling():
    alive = False
    for i in passwd_threads:
        if i.is_alive():
            alive = True
            break
    return alive

def clear():
    global map_end
    thread_tasks.clear()
    passwd_threads.clear()
    map_end = False

def join():
    for i in passwd_threads:
        i.join()