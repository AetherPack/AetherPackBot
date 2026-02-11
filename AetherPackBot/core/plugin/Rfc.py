from fastapi import FastAPI, Request
from AetherPackBot.core.plugin.manager import PluginManager
import logging

rfc = FastAPI()
plugin_manager = PluginManager()

@rfc.post("/add_plugin")
async def plugin_add_plugin(request: Request):
    """RFC-插件注册"""
    try:
        data = await request.json()
        plugin_manager.add_plugin(data)
        plugin_data_return = {
            "message": f"插件 {data.get('name')} 由 {data.get('author')} 注册成功"
        }
        return {"status": "success", "data": plugin_data_return}
    except Exception as e:
        logging.error(f"Error processing RFC request: {e}")
        return {"status": "error", "message": str(e)}
