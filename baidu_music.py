import simple_http
import pdb 
import pprint
import json 
import os.path
from collections import OrderedDict
import argparse
import socket
import re

from lxml import etree 

SONGID_XPATH = "/html/body/div/ul/li/div/span[5]/a" 
ALBUM_XPATH = "/html/body/div[4]/div/div/div[3]/div/div[1]/div[2]/div[2]/div/ul/li/div/span[5]/a[1]"
LIMIT = 100

def get_songlink(songid): 
    ret = []
    p = {
            "songids": songid
            } 
    res = simple_http.post("http://play.baidu.com/data/music/songlink", payload = p) 
    for i in json.loads(res["text"])["data"]["songList"]:
        if not i["songName"]:
            continue
        ret.append((i["songName"], i["songLink"])) 
    return ret

def get_songlinks(songs): 
    ret = []
    groups = [] 
    ng = len(songs) / LIMIT
    if len(songs) % LIMIT:
        ng += 1
    for i in range(ng):
        groups.append(",".join([song[1].strip("/song/") for song in songs[i*LIMIT:LIMIT*(i+1)]])) 
    for g in groups:
        ret.extend(get_songlink(g))
    return ret

ID_PATTERN = re.compile("/song/([0-9]{1,10})")

def get_songids(uid): 
    ret = [] 
    for i in range(0xffff):
        query = {
                "start": str(i * 25),
                "ting_uid": uid,
                "order": "hot"
                } 
        res =simple_http.get("http://music.baidu.com/data/user/getsongs", query=query); 
        if res["status"] != 200:
            break
        t = json.loads(res["text"])["data"]["html"] 
        tree = etree.HTML(t)
        result = [x for x in tree.xpath(SONGID_XPATH)] 
        if not result:
            break 
        for i in result: 
            if i.attrib.get("class"):
                continue 
            link = ID_PATTERN.match(i.attrib["href"])
            if link:
                ret.append((i.attrib["title"],
                    link.groups()[0])) 
    return ret

def download_link(name, link): 
    res = simple_http.get(link, header=simple_http.download_header, redirect=10) 
    f = open(name, "wb+")
    f.write(res["text"])
    f.close() 

def download_album(aid): 
    res = simple_http.get("http://music.baidu.com/album/%s" % aid)
    if res["status"] != 200:
        print "failed"
        print res
        exit(1)
    t = etree.HTML(res["text"])
    songs = []
    for i in t.xpath(ALBUM_XPATH):
        songs.append((i.attrib["title"], i.attrib["href"])) 
    for i, v in enumerate(songs):
        link = download_by_id(v[1].strip("/song/"))
        if not link:
            continue
        print "===================\n[%d/%d]: %s\n%s" % (i+1, len(songs), link[0], link[1]) 


def download_by_id(songid): 
    try:
        link = get_songlink(songid)[0] 
    except IndexError: 
        print "skip", songid
        return
    if os.path.exists(link[0]+".mp3"):
        return
    while True:
        try:
            download_link(link[0]+".mp3", link[1])
        except socket.error:
            continue 
        except Exception:
            print "skip", link[0] 
            return
        break
    return link


def download_author(uid): 
    dup = OrderedDict()
    jobs = get_songids(uid) 
    for k,v in jobs:
        if not k in dup:
            dup[k] = v
    jobs = dup 
    for i,v in enumerate(jobs.items()): 
        link = download_by_id(v[1].strip("/song/"))
        if not link:
            continue
        print "===================\n[%d/%d]: %s\n%s" % (i+1, len(jobs), link[0], link[1]) 


if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser(
            description="baidu mp3 downloader") 
    parser.add_argument("-i", type=str, help="download by id")
    parser.add_argument("-a", type=str, help="download by author id")
    parser.add_argument("-b", type=str, help="download by album")
    args = parser.parse_args()
    if args.i:
        link = download_by_id(args.i)
        if link:
            msg = "done: %s\n%s"
        else:
            msg = "failed: %s\n%s"
        print msg % (link[0], link[1])
    elif args.a: 
        download_author(args.a)
    elif args.b:
        download_album(args.b)
