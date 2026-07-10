"""Launcher script — sets the Windows event loop policy before uvicorn
creates its event loop. Required because Playwright needs subprocess
support, which Windows' default SelectorEventLoop doesn't provide.
"""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )