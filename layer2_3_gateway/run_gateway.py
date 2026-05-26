import sys
import asyncio

# Set the selector event loop policy on Windows before running uvicorn
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("Enforced WindowsSelectorEventLoopPolicy for psycopg async compatibility.")
    try:
        import uvicorn.loops.asyncio as uvicorn_asyncio
        uvicorn_asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop
        print("Patched uvicorn asyncio_loop_factory to SelectorEventLoop.")
    except Exception as e:
        print(f"Could not patch uvicorn loop factory: {e}")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )
