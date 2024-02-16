import aiohttp
import config
import json
import zlib

token = None
session = None
user_agent = {
    "User-Agent": "3wifiparser1.1"
}

async def get_token():
    global session,token
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent)
    resp = await session.get(config.api_url + "auth", auth=aiohttp.BasicAuth(config.login, config.password))
    if resp.status == 401:
        raise Exception("Wrong login or password")
    resp = await resp.json()
    if resp.get("ok") == True:
        token = resp.get("token")
    elif resp.get("desc") == "auth failed":
        raise Exception("Wrong login or password")
    return resp

async def get_free_task():
    global session,token
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent)
    resp = await session.get(config.api_url + "getFreeTask")
    return await resp.json()
    
async def ping_task(task_id, progress):
    global session,token
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent)
    if token == None:
        await get_token()
    resp = await (await session.get(f"{config.api_url}pingTask?task_id={task_id}&token={token}&progress={progress}")).json()
    if resp.get("ok") != True:
        if resp.get("desc") == "wrong token":
            await get_token()
    return resp

async def private_task(task_id):
    global session,token
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent)
    if token == None:
        await get_token()
    resp = await (await session.get(f"{config.api_url}privateTask?task_id={task_id}&token={token}")).json()
    if resp.get("ok") != True:
        if resp.get("desc") == "wrong token":
            await get_token()
    return resp
    
async def complete_task(result: list, task_id: int):
    global session,token
    if session == None:
        session = aiohttp.ClientSession(headers=user_agent)
    if token == None:
        await get_token()
    body = {
        "result": result,
        "task_id": task_id,
        "token": token
    }
    body = json.dumps(body).encode("utf-8")
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
    return resp