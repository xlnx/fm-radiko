import sys
import os
import json
import time
import requests
import base64
import zlib
import subprocess
import m3u8
import pytz
import tempfile
import shutil
import asyncio
import aiohttp
import aiofiles
import multiprocessing
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
import datetime
from tqdm import tqdm
from tabulate import tabulate
from queue import Queue, Empty

MAX_PENDING = multiprocessing.cpu_count() * 4
MAX_RETRY = 20

radiko = "https://radiko.jp"
radiko_player = "http://radiko.jp/apps/js/flash/myplayer-release.swf"
radiko_api = "/".join([radiko, "v2/api"])

se = requests.Session()
se.headers.update({
    "X-Radiko-App": "pc_ts",
    "X-Radiko-App-Version": "4.0.0",
    "X-Radiko-User": "test-stream",
    "X-Radiko-Device": "pc"
})

def download_player():
    player = se.get(radiko_player).content
    buf = zlib.decompress(player[8:])
    offset = 0
    rect_size = int(buf[offset] >> 3)
    rect_offset = (5 + 4 * rect_size + 7) / 8
    offset += rect_offset
    offset = int(offset + 4)

    while True:
        code = (int(buf[offset+1])<<2) + (int(buf[offset])>>6)
        l = int(buf[offset] & 0x3f)
        offset += 2
        if l == 0x3f:
            l = int(buf[offset])
            l += int(buf[offset+1])<<8
            l += int(buf[offset+2])<<16
            l += int(buf[offset+3])<<24
            offset += 4
        if code == 0:
            raise Exception("failed to extract swf")
        i = int(buf[offset]) + (int(buf[offset+1])<<8)
        if code == 87 and i == 12:
            return buf[offset+6:offset+l]
        offset += l

swf_player = download_player()

def authorize():
    buf = swf_player
    
    resp = se.post("/".join([radiko_api, "auth1_fms"]))
    auth_token = resp.headers["X-Radiko-AuthToken"]
    key_length = int(resp.headers["X-Radiko-KeyLength"])
    key_offset = int(resp.headers["X-Radiko-KeyOffset"])
    
    # print(resp.status_code)
    # print(resp.text)
    
    partial_key = base64.b64encode(buf[key_offset:key_length+key_offset])
    
    resp = se.post("/".join([radiko_api, "auth2_fms"]), headers={
        "X-Radiko-AuthToken": auth_token,
        "X-Radiko-PartialKey": partial_key
    })

    # print(resp.status_code)
    # print(resp.text)
    
    aid, _, area = resp.text.strip().split(",")
    if aid[0:2] != "JP":
        raise Exception("authorization failed: {}".format(aid))
    print("authorized: {}, {}, {}".format(aid, area, auth_token))

    se.headers.update({"X-Radiko-AuthToken": auth_token})
    return auth_token, aid, area

def get_stream_multi_url(station_id):
    resp = se.get("/".join([radiko, "v2/station/stream_multi/{}.xml".format(station_id)]))
    return [{
        "areafree": bool(int(x.attrib["areafree"])),
        "url": x.text
    } for x in ET.fromstring(resp.content)]

def into_tokyo_time(time_str, local=True):
    day, time = time_str.split(" ")
    h, m, s = time.split(":")
    h, m, s = int(h), int(m), int(s)
    det = datetime.timedelta(hours=h, minutes=m, seconds=s)
    t = datetime.datetime.strptime(day, "%Y-%m-%d") + det
    if local:
        t = t.astimezone(pytz.timezone("Asia/Tokyo"))
    print(t.strftime("%Y-%m-%d %H:%M:%S"))
    rt = t - datetime.timedelta(hours=5)
    print(rt.strftime("%Y-%m-%d %H:%M:%S"))
    return t, t.strftime("%Y%m%d%H%M%S"), rt.strftime("%Y%m%d")

def get_stations(date=None):
    if date is not None:
        resp = se.get("/".join([radiko, "v3/program/date", date, "{}.xml".format(area_id)]))
    else:
        resp = se.get("/".join([radiko_api, "program/now"]), params={"area_id": area_id})
    root = ET.fromstring(resp.content)
    def programs(x):
        return {
            "date": x.find("date").text,
            "progs": [{
                "ft": z.attrib["ft"],
                "to": z.attrib["to"],
                "ftl": z.attrib["ftl"],
                "tol": z.attrib["tol"],
                "dur": z.attrib["dur"],
                "title": z.find("title").text,
                # "sub_title": z.find("sub_title").text,
                "desc": z.find("desc").text,
                "pfm": z.find("pfm").text,
                "info": z.find("info").text,
                "url": z.find("url").text,
            } for z in x.findall("prog")]
        } if x is not None else None
    def scd(x):
        return programs(x.find("progs")) if x is not None else None
    stations = [{
        "id": x.attrib["id"],
        "name": x.find("name").text,
        "progs": programs(x.find("progs")),
        "scd": scd(x.find("scd"))
    } for x in root.find("stations").findall("station")]
    return stations

def get_program_by_start_time(station_id, sec, date):
    stations = get_stations(date)
    for x in (x for x in stations if x["id"] == station_id):
        for p in x["progs"]["progs"]:
            if p["ft"] == sec:
                return p

    for x in (x for x in stations if x["id"] == station_id):
        print(tabulate([[  
            datetime.datetime.strptime(y["ft"], "%Y%m%d%H%M%S").strftime("%m-%d %H:%M"),
            int(y["dur"]) / 60, y["title"]
        ] for y in x["progs"]["progs"]], headers=["Since", "Duration(min)", "Title"]))
        break
    else:
        raise Exception("station not found")
    raise Exception("program not found")

def get_chunklist(station_id, prog):
    resp = se.post("/".join([radiko_api, "ts/playlist.m3u8"]), params={
        "station_id": station_id,
        "ft": prog["ft"],
        "to": prog["to"],
        "l": '15'
    })
    resp = se.get(m3u8.loads(resp.text).playlists[0].uri)
    return [s.uri for s in m3u8.loads(resp.text).segments]

async def fetch_chunk(chunks, workdir, files):
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
                        print("retry #{}: {}".format(rep, e))
                async with lbar:
                    bar.update(1)
            except Empty:
                return
    async with aiohttp.ClientSession() as s:
        await asyncio.gather(*[one_thread(s, i) \
                               for i in range(0, MAX_PENDING)])
    bar.close()
        
def bulk_download(chunks, output):
    workdir = tempfile.mkdtemp()
    try:
        print("downloading chunks...")
        files = Queue()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(fetch_chunk(chunks, workdir, files))
        lname = os.path.join(workdir, "aac_list")
        oname = os.path.join(workdir, "joint.aac")
        print("indexing chunks...")
        with open(lname, "w") as f:
            while not files.empty():
                fname = files.get()
                f.write("file {}\n".format(os.path.abspath(fname)))
        args = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", lname,
            "-c", "copy",
            "-y",
            oname
        ]
        print("merging chunks...")
        print("$ " + " ".join(args))
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print(proc.returncode)
        args = [
            "ffmpeg",
            "-i", oname,
            "-c:a", "libmp3lame",
            "-ac", "2",
            "-q:a", "2",
            "-hide_banner",
            "-loglevel", "info",
            "-y",
            output
        ]
        print("converting to mp3...")
        print("$ " + " ".join(args))
        proc = subprocess.run(args, stdout=subprocess.PIPE)
        print("download complete!! -> {}".format(os.path.abspath(output)))
        # print(proc.returncode)
    finally:
        shutil.rmtree(workdir)

def download_stream(station_id, nsecs, output):
    stream_urls = get_stream_multi_url(station_id)
    stream_url = next(x["url"] for x in stream_urls if x["areafree"]) # areaid
    print(stream_url)
    rtmpdump = subprocess.Popen([
        "rtmpdump",
        "--live", 
        "-r", stream_url,
        "--conn", 'S:""',
        "--conn", 'S:""',
        "--conn", 'S:""',
        "--conn", "S:{}".format(auth_token),
        "--swfVfy", radiko_player,
        "--stop", "{}".format(nsecs),
        "--timeout", "180",
        "--flv", "-",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("start streaming...")
    print("$ " + " ".join(rtmpdump.args))
    ffmpeg = subprocess.Popen([
        "ffmpeg",
        "-i", "-",
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "44100",
        "-ab", "64k",
        "-ac", "2",
        "-hide_banner",
        "-loglevel", "info",
        "-y",
        output
    ], stdin=rtmpdump.stdout, stdout=subprocess.PIPE)
    print("$ " + " ".join(ffmpeg.args))
    rtmpdump.stdout.close()
    out = ffmpeg.communicate()
    print("stream complete!! -> {}".format(os.path.abspath(output)))
        
if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("tool", type=str, help="tool name: { rec, rec-live }")
    
    parser.add_argument("-t", "--time", dest="nsecs", help="stream record time(sec)", default=60)
    parser.add_argument("-o", "--output", dest="output", help="output file", default="a.mp3")
    parser.add_argument("-s", "--station", dest="station_id", help="station id")
    parser.add_argument("-f", "--from", dest="start", help="rec start timestamp: Y-M-D H:M:S")
    args = parser.parse_args(sys.argv[1:])

    if args.tool == "rec":
        auth_token, area_id, area = authorize()
        with open("/tmp/a.swf", "wb") as f:
            f.write(swf_player)
        tokyo, sec, date = into_tokyo_time(args.start)
        # print(tokyo.strftime("%Y-%m-%d %H:%M:%S"))
        "2019-09-17 22:00:00"
        prog = get_program_by_start_time(args.station_id, sec, date)
        print(tabulate([[
            args.station_id,
            tokyo.strftime("%Y-%m-%d %H:%M:%S"),
            prog["title"]
        ]], headers=["Station", "Since(Tokyo)", "Title"]))
        chunks = get_chunklist(args.station_id, prog)
        bulk_download(chunks, output=args.output)
    elif args.tool == "rec-live":
        auth_token, area_id, area = authorize()
        print(tabulate([[
            args.station_id,
            args.nsecs,
        ]], headers=["Station", "Duration(sec)"]))
        download_stream(args.station_id, nsecs=args.nsecs, output=args.output)
    elif args.tool == "list":
        auth_token, area_id, area = authorize()
        stations = get_stations()
        print(tabulate([[  
            x["id"], x["name"], x["scd"]["progs"][0]["title"]
        ] for x in stations], headers=["Id", "Station", "Current"]))
    else:
        print("unknown tool name: {}".format(tool))

