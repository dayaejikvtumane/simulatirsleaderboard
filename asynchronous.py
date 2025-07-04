# для асинхрона
import asyncio
from functools import wraps


def async_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Ошибка в асинхронном обработчике: {e}")
            raise

    return wrapper


async def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, func, *args)
    except Exception as e:
        print(f"Ошибка {e}")
        raise
