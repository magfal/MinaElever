import json

def toast(response, message, level="success", duration=5000, reswap=None):
    response.headers["HX-Trigger"] = json.dumps({
        "showToast": {
            "message": message,
            "level": level,
            "duration": duration
        }
    })
    if reswap:
        response.headers["HX-Reswap"] = reswap
    return response