import aiohttp
import config

token = None
session = None

async def get_token():
    global session,token
    if session == None:
        session = aiohttp.ClientSession()
    resp = await (await session.get(config.api_url + "auth", auth=aiohttp.BasicAuth(config.login, config.password))).json()
    if resp["ok"]:
        token = resp["token"]
    return resp

async def get_free_task():
    global session,token
    if session == None:
        session = aiohttp.ClientSession()
    resp = await session.get(config.api_url + "getFreeTask")
    return await resp.json()
    
async def ping_task(task_id, progress):
    global session,token
    if session == None:
        session = aiohttp.ClientSession()
    if token == None:
        await get_token()
    resp = await (await session.get(f"{config.api_url}pingTask?task_id={task_id}&token={token}&progress={progress}")).json()
    if not(resp["ok"]):
        if resp.get("desc") == "wrong token":
            await get_token()
    return resp

async def private_task(task_id):
    global session,token
    if session == None:
        session = aiohttp.ClientSession()
    if token == None:
        await get_token()
    resp = await (await session.get(f"{config.api_url}privateTask?task_id={task_id}&token={token}")).json()
    if not(resp["ok"]):
        if resp.get("desc") == "wrong token":
            await get_token()
    return resp
    
async def complete_task(result: list, task_id: int):
    global session,token
    if session == None:
        session = aiohttp.ClientSession()
    if token == None:
        await get_token()
    body = {
        "result": result,
        "task_id": task_id,
        "token": token
    }
    resp = await session.post(f"{config.api_url}closeTask", json=body)
    resp = await resp.json()
    if not(resp["ok"]):
        if resp.get("desc") == "wrong token":
            await get_token()
    return resp