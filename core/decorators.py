import random
import time
from functools import wraps
from tqdm import tqdm
from config import SLEEP_TIME
from logger import logger


def retry_on_error(tries: int, exception_message: str = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(tries):
                result = func(*args, **kwargs)
                if result is None or result is False:
                    try:
                        for _ in tqdm(range(random.randint(*SLEEP_TIME)), colour="green"):
                            time.sleep(1)

                    except Exception as e:
                        logger.error(f"Sleep error: {str(e)}")
                else:
                    return result
            if exception_message is None:
                return False
            else:
                raise Exception(exception_message)

        return wrapper

    return decorator
