import asyncio


def console_main() -> None:
    from .main import main as async_main
    asyncio.run(async_main())


