from typing import Dict, List
from fastapi import HTTPException
import logging

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, Dict] = {}
    
    def add_plugin(self, plugin_data: Dict) -> bool:
        """添加插件"""
        try:
            # 验证必要字段
            if 'name' not in plugin_data or 'author' not in plugin_data:
                raise HTTPException(
                    status_code=400,
                    detail="缺少必要的插件信息: name 和 author"
                )
            
            plugin_name = plugin_data['name']
            self.plugins[plugin_name] = {
                'name': plugin_name,
                'author': plugin_data['author'],
                'status': 'active'
            }
            logging.info(f"成功注册插件: {plugin_name} by {plugin_data['author']}")
            return True
            
        except Exception as e:
            logging.error(f"注册插件失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_plugins(self) -> List[Dict]:
        """获取所有插件"""
        return list(self.plugins.values())
    
    def remove_plugin(self, name: str) -> bool:
        """移除插件"""
        if name in self.plugins:
            del self.plugins[name]
            logging.info(f"已移除插件: {name}")
            return True
        return False
    
    def get_plugin(self, name: str) -> Dict:
        """获取单个插件"""
        plugin = self.plugins.get(name)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"插件 {name} 未找到")
        return plugin
