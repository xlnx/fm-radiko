import sys
import os
import json
import time
import requests
import m3u8
import tempfile
import shutil
import subprocess
import inquirer
import dl
from argparse import ArgumentParser

se = requests.Session()
prefix = "https://d3cfw2mckicdfw.cloudfront.net/4aaea307daf6beef6bf5ecb7b610e19efeb8dd5530"

def get_playlist():
    resp = se.get("{}/playlist.m3u8".format(prefix))
    ll = m3u8.loads(resp.text).playlists
    l = []
    for e in ll:
        f = {
            'url': e.uri
        }
        f.update(e.stream_info.__dict__)
        l.append(f)
    return l

def get_chunks(url):
    resp = se.get("{}/{}".format(prefix, url))
    ll = m3u8.loads(resp.text).segments
    cli = url.split('/')[0]
    # mid = (ll[0].uri.split('_')[0]).split('-')[1][1:]
    return ["{}/{}/{}".format(prefix, cli, x.uri) for x in ll]

def select_chunklist(pl):
    def fn(x):
        a, b = x['resolution']
        bw = x['bandwidth']
        fps = x['frame_rate']
        return (-a*b, -fps, -bw)
    pl.sort(key=fn)
    choices = {
        "res:{}x{} fps:{} {}".format(
            e['resolution'][0],
            e['resolution'][1],
            e['frame_rate'],
            e['video']
        ): e
        for e in pl
    }
    quests = [
        inquirer.List(
            'source',
            message='select a m3u8 source:',
            choices=choices.keys()
        )
    ]
    ans = inquirer.prompt(quests)
    pl = choices[ans['source']]
    a, b = pl['resolution']
    bw = pl['bandwidth']
    fps = pl['frame_rate']
    print("url: {}".format(pl['url']))
    print("resolution: {}x{}".format(a, b))
    print("bandwidth: {}".format(bw))
    print("fps: {}".format(fps))
    print("video: {}".format(pl['video']))
    return pl

if __name__ == "__main__":

    parser = ArgumentParser()

    parser.add_argument("-u", "--url", dest="url", help="url")
    parser.add_argument("-o", "--output", dest="output", help="output file", default="a.ts")
    args = parser.parse_args(sys.argv[1:])

    prefix = args.url

    pl = get_playlist()
    cl = select_chunklist(pl)['url']
    chs = get_chunks(cl)
    
    output = args.output
    
    workdir = tempfile.mkdtemp()
    try:
        files = dl.download_chunks(chs, workdir)
        lname = os.path.join(workdir, "chunk_list")
        # oname = os.path.join(workdir, "joint.ts")
        print("indexing chunks")
        with open(lname, "w") as f:
            for fname in files:
                f.write("file {}\n".format(os.path.abspath(fname)))
        args = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", lname,
            "-c", "copy",
            "-y",
            output
        ]
        print("merging chunks...")
        print("$ " + " ".join(args))
        proc = subprocess.run(args)
    finally:
        shutil.rmtree(workdir)
    
# , headers={
#     'Origin': 'https://www.openrec.tv',
#     'Referer': 'https://www.openrec.tv/live/12rog4w16zn',
#     'Sec-Fetch-Mode': 'cors'
# })
