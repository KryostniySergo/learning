import time
from functools import wraps

def counter(func):
    wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        res = func()
        end = time.perf_counter()
        print(end - start)
        return res 
    return wrapper


@counter
def slow():
    return sum(range(10**6))

slow()