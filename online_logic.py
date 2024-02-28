import database
import cloud
import json
import utils
import asyncio
import logging
from random import getrandbits

#SSID,BSSID,format,sec,passwords,WPS_keys,lat,lon,time,scanned_time

async def load_task_to_server(random_subtask_id, server_task_id):
    data = database.get_nets(random_subtask_id)
    for it in range(10):
        ans = await cloud.complete_task(data, server_task_id)
        if not(ans.get("ok")):
            if ans.get("desc") == "task is free":
                logging.warning("### TASK IS FREE ###")
                reprivate = await cloud.private_task(server_task_id)
                if not(reprivate.get("ok")):
                    logging.error("### REPRIVATE ERROR ###")
                    break
                else:
                    logging.warning("### REPRIVATE SUCCESS ###")
                ans = await cloud.complete_task(data, server_task_id)
                if not(ans.get("ok")):
                    logging.error("### RECOMPLETE FAILURE ###")
                else:
                    logging.warning("### RECOMPLETE SUCCESS ###")
                break
            else:
                logging.error("### COMPLETE ERROR ###\n" + str(ans.get("desc")))
        else:
            break

async def get_task_from_server():
    logging.info("Receiving a task from the server...")
    out_task = utils.Task()
    task = await cloud.get_free_task()
    private = False
    for i in range(5):
        if task.get("ok"):
            logging.info("Privating task...")
            task = task["data"]
            out_task.min_maxTileX = json.loads(task["min_maxTileX"])
            out_task.min_maxTileY = json.loads(task["min_maxTileY"])
            out_task.progress = json.loads(task["min_max_progress"])
            out_task.max_area = task["max_area"]
            out_task.local_id = getrandbits(32)
            out_task.server_id = task["id"]
            privateresult = await cloud.private_task(task["id"])
            if privateresult.get("ok") == True:
                private = True
                break
            elif privateresult.get("desc") == "task privated":
                task = await cloud.get_free_task()
        else:
            if task.get("desc") == "no more tasks":
                logging.info("No more tasks. Wait 1 minute...")
                await asyncio.sleep(60)
                return None
            else:
                logging.error("Invalid task from server")
    if not(private):
        return None
    return out_task