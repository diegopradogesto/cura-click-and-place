from . import ClickAndPlace

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

def getMetaData():
    return {
        "tool": {
            "name": i18n_catalog.i18nc("@label", "Click and Place"),
            "description": i18n_catalog.i18nc("@info:tooltip", "Click on a 3D model face and place that face down."),
            "icon": "tool_icon.svg",
            "weight": 5
        }
    }

def register(app):
    return { "tool": ClickAndPlace.ClickAndPlace() }
