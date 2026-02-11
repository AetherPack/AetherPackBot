from fastapi import FastAPI, Request, HTTPException
from AetherPackBot.core.plugin.manager import PluginManager, PluginError, PluginValidationError, PluginNotFoundError
import logging

rfc = FastAPI()
plugin_manager = PluginManager()

@rfc.post("/add_plugin")
async def plugin_add_plugin(request: Request):
    """RFC-插件注册"""
    try:
        data = await request.json()
        await plugin_manager.add_plugin(data)
        plugin_data_return = {
            "message": f"插件 {data.get('name')} 由 {data.get('author')} 注册成功"
        }
        return {"status": "success", "data": plugin_data_return}
    except PluginValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PluginError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing RFC request: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
