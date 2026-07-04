from typing import Dict, Any

class SystemState:
    def __init__(self):
        # Default configuration aligned with new frontend UI
        self.config = {
            "crawler": {
                "mode": "manual",      # "manual", "daily", "interval"
                "value": "08:00"       # "08:00" or "60" (minutes)
            },
            "ai": {
                "mode": "manual",      # "manual", "daily", "interval"
                "value": "15",         # minutes
                "batch_size": 50       # default 50, 0 means all
            }
        }

    def update_config(self, new_config: Dict[str, Any]):
        if "crawler" in new_config:
            self.config["crawler"].update(new_config["crawler"])
        if "ai" in new_config:
            self.config["ai"].update(new_config["ai"])

system_state = SystemState()
