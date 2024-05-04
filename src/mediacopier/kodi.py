from kodipydent import Kodi

from console.console import console
from models.store import store


def connect_to_kodi_or_die():
    try:
        store.kodi = Kodi(hostname=store.kodi_ip,
                          port=store.kodi_jsonrpc_port,
                          username=store.kodi_username,
                          password=store.kodi_password)

    except Exception:
        console.log("Couldn't reach Kodi, so exiting here...", style="danger")
        console.print_exception()
        exit(1)

    # Run a basic ping test, die on failure
    json_result = store.kodi.JSONRPC.Ping()
    if json_result:
        console.log("Kodi json response:", style="info")
        console.log(json_result)
    if json_result and 'pong' in json_result['result']:
        console.log(":ping_pong: Successfully reached Kodi -> ping <> pong :ping_pong:", style='success')
    else:
        console.log("Couldn't communicate with Kodi, exiting here", style="danger")
        exit(1)
