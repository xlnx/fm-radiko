# Requirements

* Python 3.* with following packages installed:
  * requests
  * m3u8
  * asyncio
  * aiohttp
  * aiofiles
  * tqdm
  * tabulate

* rtmpdump
* ffmpeg

# Usage

```bash
$ python a.py list
authorized: JP13, tokyo Japan, c-2IQ3Up65q3ih_H8jNlSA
Id              Station       Current
--------------  ------------  -----------------------------
TBS             TBSラジオ        新井麻希 Fine！！
QRR             文化放送          走れ！歌謡曲
LFR             ニッポン放送        King Gnu井口理のオールナイトニッポン0(ZERO)
RN1             ラジオNIKKEI第1   番組休止中
RN2             ラジオNIKKEI第2   放送休止中
INT             InterFM897    THE GOOD MIXER
FMT             TOKYO FM      大家志津香のウィズモ！-WIZ MOMENT-
FMJ             J-WAVE        TOKYO M.A.A.D SPIN
JORF            ラジオ日本         Midnight Mix
BAYFM78         bayfm78       Song of Japan(2)
NACK5           NACK5         ラジオのアナ～ラジアナ（木）
YFM             ＦＭヨコハマ        Hits 200
HOUSOU-DAIGAKU  放送大学          番組休止中
JOAK            NHKラジオ第1（東京）  ラジオ深夜便▽にっぽんの歌こころの歌
JOAK-FM         NHK-FM（東京）    ラジオ深夜便▽にっぽんの歌こころの歌 
```

```bash
$ python a.py rec -s QRR -f "2019-09-18 25:30:00"
authorized: JP13, tokyo Japan, yIcz5H-L6moe0MqyphOFIQ
2019-09-19 02:30:00
2019-09-18 21:30:00
Station    Since(Tokyo)         Title
---------  -------------------  -----------------
QRR        2019-09-19 02:30:00  鹿乃のかくかくしかじかありまして！
downloading chunks...
100%|██████████████████████████████████| 360/360 [00:07<00:00, 46.66p/s]
indexing chunks...
merging chunks...
> ffmpeg -f concat -safe 0 -i /tmp/tmpso5wiv9b/aac_list -c copy -y /tmp/tmpso5wiv9b/joint.aac
converting to mp3...
> ffmpeg -i /tmp/tmpso5wiv9b/joint.aac -c:a libmp3lame -ac 2 -q:a 2 -hide_banner -loglevel info -y a.mp3
[aac @ 0x556edf9c7d00] Estimating duration from bitrate, this may be inaccurate
Input #0, aac, from '/tmp/tmpso5wiv9b/joint.aac':
  Duration: 00:31:05.55, bitrate: 46 kb/s
    Stream #0:0: Audio: aac (HE-AAC), 48000 Hz, stereo, fltp, 46 kb/s
Stream mapping:
  Stream #0:0 -> #0:0 (aac (native) -> mp3 (libmp3lame))
Press [q] to stop, [?] for help
Output #0, mp3, to 'a.mp3':
  Metadata:
    TSSE            : Lavf58.29.100
    Stream #0:0: Audio: mp3 (libmp3lame), 48000 Hz, stereo, fltp
    Metadata:
      encoder         : Lavc58.54.100 libmp3lame
size=   33427kB time=00:30:00.00 bitrate= 152.1kbits/s speed=76.3x    
video:0kB audio:33427kB subtitle:0kB other streams:0kB global headers:0kB muxing overhead: 0.000692%
download complete!! -> /home/koishi/fm/a.mp3
```

```bash
$ python a.py rec -s QRR -f "2019-09-18 25:20:00"
authorized: JP13, tokyo Japan, lGFOmkCQF9S7TMjLQZYX5Q
2019-09-19 02:20:00
2019-09-18 21:20:00
Since          Duration(min)  Title
-----------  ---------------  ----------------------
09-18 05:00               30  おはよう寺ちゃん活動中  第1部
09-18 05:30                9  聖教新聞ラジオライブラリー「新・人間革命」
09-18 05:39               81  おはよう寺ちゃん活動中 第2部
09-18 07:00               60  なな→きゅう 7時台
09-18 08:00               60  なな→きゅう 8時台
09-18 09:00              120  くにまるジャパン 極 9時～11時
09-18 11:00              120  くにまるジャパン 極 11時～13時
09-18 13:00              150  大竹まこと ゴールデンラジオ！
09-18 15:30              140  斉藤一美 ニュースワイドＳＡＫＩＤＯＲＩ！
09-18 17:50                7  文化放送ライオンズナイター プロ野球直前情報
09-18 17:57               63  文化放送ライオンズナイター 18時
09-18 19:00               60  文化放送ライオンズナイター 19時
09-18 20:00               60  文化放送ライオンズナイター 20時
09-18 21:00               30  文化放送ライオンズナイター 21時
09-18 21:30               30  編集長 稲垣吾郎
09-18 22:00               60  レコメン！22時台
09-18 23:00               60  レコメン！23時台
09-19 00:00               60  レコメン！24時台
09-19 01:00               60  &CAST!!!アワー ラブナイツ！
09-19 02:00               30  和牛のモーモーラジオ
09-19 02:30               30  鹿乃のかくかくしかじかありまして！
09-19 03:00              120  走れ！歌謡曲
Traceback (most recent call last):
  File "a.py", line 309, in <module>
    prog = get_program_by_start_time(args.station_id, sec, date)
  File "a.py", line 164, in get_program_by_start_time
    raise Exception("program not found")
Exception: program not found
```

```bash
$ python a.py rec-live -s QRR -t 20
authorized: JP13, tokyo Japan, nyS-KaXJCJ_dMx6MPHni7g
Station      Duration(sec)
---------  ---------------
QRR                     20
rtmpe://c-radiko.smartstream.ne.jp/QRR/_definst_/simul-stream.stream
start streaming...
> rtmpdump --live -r rtmpe://c-radiko.smartstream.ne.jp/QRR/_definst_/simul-stream.stream --conn S:"" --conn S:"" --conn S:"" --conn S:nyS-KaXJCJ_dMx6MPHni7g --swfVfy http://radiko.jp/apps/js/flash/myplayer-release.swf --stop 20 --timeout 180 --flv -
> ffmpeg -i - -vn -acodec libmp3lame -ar 44100 -ab 64k -ac 2 -hide_banner -loglevel info -y a.mp3
Input #0, flv, from 'pipe:':
  Metadata:
    StreamTitle     : 
  Duration: N/A, start: 0.000000, bitrate: N/A
    Stream #0:0: Audio: aac (HE-AAC), 48000 Hz, stereo, fltp
Stream mapping:
  Stream #0:0 -> #0:0 (aac (native) -> mp3 (libmp3lame))
Output #0, mp3, to 'a.mp3':
  Metadata:
    StreamTitle     : 
    TSSE            : Lavf58.29.100
    Stream #0:0: Audio: mp3 (libmp3lame), 44100 Hz, stereo, fltp, 64 kb/s
    Metadata:
      encoder         : Lavc58.54.100 libmp3lame
size=     157kB time=00:00:20.06 bitrate=  64.2kbits/s speed=80.4x    
video:0kB audio:157kB subtitle:0kB other streams:0kB global headers:0kB muxing overhead: 0.172366%
stream complete!! -> /home/koishi/fm/a.mp3
```

