import requests
import base64
import zlib
import xml.etree.ElementTree as ET
import subprocess
from optparse import OptionParser
import sys
import os

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
    
    a, _, b = resp.text.strip().split(",")
    if a[0:2] != "JP":
        raise Exception("authorization failed: {}".format(a))
    print("authorized: {}, {}, {}".format(a, b, auth_token))

    se.headers.update({"X-Radiko-AuthToken": auth_token})
    return auth_token

def get_stream_multi_url(station_id):
    resp = se.get("/".join([radiko, "v2/station/stream_multi/{}.xml".format(station_id)]))
    return [{
        "areafree": bool(int(x.attrib["areafree"])),
        "url": x.text
    } for x in ET.fromstring(resp.content)]

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-t", "--time", dest="nsecs", help="record time(sec)", default=10)
    parser.add_option("-o", "--output", dest="output", help="output file", default="a.mp3")
    opts, args = parser.parse_args(sys.argv[1:])
    
    auth_token = authorize()
    stream_urls = get_stream_multi_url("QRR")
    stream_url = next(x["url"] for x in stream_urls if x["areafree"]) # areaid
    print(stream_url)
    with open("/tmp/a.swf", "wb") as f:
        f.write(swf_player)
    rtmpdump = subprocess.Popen([
        "rtmpdump",
        "--live", 
        "-r", stream_url,
        "--conn", 'S:""',
        "--conn", 'S:""',
        "--conn", 'S:""',
        "--conn", "S:{}".format(auth_token),
        "--swfVfy", radiko_player,
        "--stop", "{}".format(opts.nsecs),
        "--timeout", "180",
        "--flv", "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print(" ".join(rtmpdump.args))
    # print(rtmpdump.returncode)
    # print(rtmpdump.stderr.decode("utf8"))
    ffmpeg = subprocess.Popen([
        "ffmpeg",
        "-i", "-",
        "-vn",
        # "-acodec", "copy",
        # "/tmp/a.aac"
        "-acodec", "libmp3lame",
        "-ar", "44100",
        "-ab", "64k",
        "-ac", "2",
        opts.output
    ], stdin=rtmpdump.stdout)
    rtmpdump.stdout.close()
    output = ffmpeg.communicate()

