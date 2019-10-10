import os
import asyncio
import aiohttp
import aiofiles
import multiprocessing
from tqdm import tqdm
from queue import Queue, Empty

MAX_PENDING = multiprocessing.cpu_count() * 4
MAX_RETRY = 20

async def fetch_chunk(chunks, workdir, files, headers={}):
    q = Queue()
    for e in chunks:
        q.put_nowait(e)
    lock = asyncio.Lock()
    lbar = asyncio.Lock()
    bar = tqdm(ncols=72, unit="p", total=len(chunks))
    async def one_thread(s, i):
        while True:
            try:
                async with lock:
                    uri = q.get_nowait()
                    _, name = os.path.split(uri)
                    fname = os.path.join(workdir, name)
                    files.put(fname)
                for rep in range(0, MAX_RETRY):
                    try:
                        async with s.get(uri, timeout=10) as resp:
                            async with aiofiles.open(fname, "wb") as f:
                                await f.write(await resp.read())
                        break
                    except Exception as e:
                        pass
                        # print("retry #{}: {}".format(rep, e))
                async with lbar:
                    bar.update(1)
            except Empty:
                return
    async with aiohttp.ClientSession(headers=headers) as s:
        await asyncio.gather(*[one_thread(s, i) \
                               for i in range(0, MAX_PENDING)])
    bar.close()

def download_chunks(chunks, workdir, headers={}):
    files = Queue()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_chunk(chunks, workdir, files, headers=headers))
    l = []
    while not files.empty():
        l.append(files.get())
    return l
