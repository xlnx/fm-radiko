import os
import sys
import ass
import json
import datetime
import requests

# lobby = "lv81jqyw289"
# start_time = "2019-04-04T05:56:58"
# raw_time = (1,24,21)
# local_time = (1,25,1)
# tag = 0

# lobby = "wez96pl0mzl"
# start_time = "2019-04-04T10:02:12"
# raw_time = (1,29,19)
# local_time = (1,30,2)
# tag = 1

# lobby = "6oz3j67k783"
# start_time = "2019-04-05T09:48:20"
# raw_time = (0,40,39)
# local_time = (0,40,58)
# tag = 1.5

# lobby = "12rog4w16zn"
# start_time = "2019-04-05T10:40:58"
# raw_time = (1,9,11)
# local_time = (1,9,44)
# tag = 2

# lobby = "d1rngejw58v"
# start_time = "2019-04-09T11:21:33"
# raw_time = (1,55,38)
# local_time = (1,56,33)
# tag = 3

# lobby = "12rog5e2lzn"
# start_time = "2019-05-25T04:21:40"
# raw_time = (1,1,39)
# local_time = (1,2,9)
# tag = 4

# lobby = "olryknekoz2"
# start_time = "2019-06-09T11:51:48"
# raw_time = (1,4,12)
# local_time = (1,4,43)
# tag = 5

se = requests.Session()
url = "https://public.openrec.tv/external/api/v5/movies/{}/chats?from_created_at={}.000Z&is_including_system_message=false"

# json.dump(r, open("chats.json", "w"), indent=2)

if __name__ == "__main__":
    r = []
    start_time = datetime.datetime.strptime(start_time + "+00:00", '%Y-%m-%dT%H:%M:%S%z')
    y = datetime.datetime.strftime(start_time, '%Y-%m-%dT%H:%M:%S')
    while True:
        l = se.get(url.format(lobby, y)).json()
        if len(l):
            e = l[-1]

            t = datetime.datetime.strptime(e['posted_at'], '%Y-%m-%dT%H:%M:%S%z') + datetime.timedelta(seconds=1)
            t = datetime.datetime.utcfromtimestamp( t.timestamp() )

            y = datetime.datetime.strftime(t, '%Y-%m-%dT%H:%M:%S%z')
        else:
            break
        r += l
        print(l[0]['posted_at'], l[0]['message'])

    msgs = r #json.load(open("chats.json", "r"))
    json.dump(msgs, open("chats.{}.json".format(tag), "w"), indent=2)

    doc = ass.document.Document()
    doc.play_res_x = 560
    doc.play_res_y = 420

    styl = ass.document.Style()
    styl.fontsize = 26
    styl.secondary_color = ass.document.Color.WHITE
    styl.back_color = ass.document.Color(32, 32, 32)
    styl.outline = 0.5
    doc.styles.append(styl)

    print(doc.styles[0].__dict__)
    s = start_time
    print(s)
    i = 0
    slots = []
    def fff(x):
        a, b, c = x
        return a * 60**2 + b * 60 + c
    scale = fff(local_time) / fff(raw_time)
    xw = styl.fontsize * 0.85
    elapse = datetime.timedelta(seconds=16)
    for msg in msgs:
        t = datetime.datetime.strptime(msg['posted_at'], '%Y-%m-%dT%H:%M:%S%z')
        dlg = ass.document.Dialogue()
        dt = (t - s) * scale # 1.0079035763683066
        dlg.start = dt #datetime.timedelta(seconds=1,microseconds=40000)
        dlg.end = dt + elapse
        dlg.style = 'Default'
        txt = msg['message']
        uid = msg['user']['nickname']
        ucol = msg['chat_setting']['name_color'][1:].upper()
        tcol = 'FFFFFF'
        l = 0
        for e in uid + " " +txt:
            c = ord(e)
            if c < 0x0020 or c > 0x7e:
                l += xw # 12.5
            else:
                l += xw / 2 # 4.5
        l /= 1.3
        x = 560# + l
        y = 0
        iv = elapse / (x + l)
        for i, (t0, l0, iv0, _) in enumerate(slots):
            if t - t0 > l0 * iv0 and (t - t0 >= elapse or elapse + t0 - t < 560 * iv):
                y = i
                slots[i] = (t, l, iv, txt)
                break
            y = y + 1
        else:
            slots.append((t, l, iv, txt))
        y = (y + 1) * 25
        # mov = "\\an6\pos(0,0)"
        mov = "\\an4\move({},{},{},{})".format(x, y, -l, y)
        dlg.text = "{{{}\c&H{}\\fs-3.5\\b1}}".format(mov, ucol) + uid + " " + "{{\\b0\\fs+5.385\c&H{}}}".format(tcol) + txt
        doc.events.append(dlg)
        # print(dlg.start)
        # print(dlg.end)
        i = i + 1
    print(doc.events[0].__dict__)
    # print(ass.document.Dialogue.__dict__.keys())

    with open("chats.{}.ass".format(tag), "w") as f:
        doc.dump_file(f)
