from fastapi import FastAPI,Request

rfc = FastAPI()

@rfc.post("/plugin")
async def plugin_rfc(self,):
    """RFC数据获取"""
    data = await Request.json()
