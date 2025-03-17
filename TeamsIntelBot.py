#!/usr/bin/env python3  
# -*- coding: utf-8 -*- 
#----------------------------------------------------------------------------
# Created By  : Julien Mousqueton @JMousqueton
# Original By : VX-Underground 
# Created Date: 22/08/2022
# Version     : 3.0.0 (2023-05-15)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports 
# ---------------------------------------------------------------------------
import feedparser
import time, requests
import csv  # Feed.csv
import sys  # Python version 
import json, hashlib  # Ransomware feed via ransomware.live 
from configparser import ConfigParser
import os  # Webhook OS Variable and Github action 
from os.path import exists
from optparse import OptionParser
import urllib.request
from bs4 import BeautifulSoup  # parse redflag 
from datetime import datetime, timedelta
import re

# ---------------------------------------------------------------------------
# Function to send MS-Teams card 
# ---------------------------------------------------------------------------
def Send_Teams(webhook_url: str, content: str, title: str, color: str = "000000") -> int:
    response = requests.post(
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        json={
            "themeColor": color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": content
            }],
        },
    )
    return response.status_code  # Should be 200

# ---------------------------------------------------------------------------
# Function to add Emoji 
# ---------------------------------------------------------------------------
def Emoji(feed):
    match feed:
        case "Leak-Lookup": Title = '💧 '
        case "VERSION": Title = '🔥 '
        case "DataBreaches": Title = '🕳 '
        case "FR-CERT Alertes" | "FR-CERT Avis": Title = '🇫🇷 '
        case "EU-ENISA Publications": Title = '🇪🇺 '
        case "Cyber-News": Title = '🕵🏻‍♂️ '
        case "Bleeping Computer": Title = '💻 '
        case "Microsoft Sentinel": Title = '🔭 '
        case "Hacker News": Title = '📰 '
        case "Cisco": Title = '📡 '
        case "Securelist": Title = '📜 '
        case "ATT": Title = '📞 '
        case "Google TAG": Title = '🔬 '
        case "DaVinci Forensics": Title = '📐 '
        case "VirusBulletin": Title = '🦠 '
        case "Information Security Magazine": Title = '🗞 '
        case "US-CERT CISA": Title = '🇺🇸 '
        case "NCSC": Title = '🇬🇧 '
        case "SANS": Title = '🌍 '
        case "malpedia": Title = '📖 '
        case "Unit42": Title = '🚓 '
        case "Microsoft Security": Title = 'Ⓜ️ '
        case "Checkpoint Research": Title = '🏁 '
        case "Proof Point": Title = '🧾 '
        case "RedCanary": Title = '🦆 '
        case "MSRC Security Update": Title = '🚨 '
        case "CIRCL Luxembourg": Title = '🇱🇺 '
        case _: Title = '📢 '
    return Title

# ---------------------------------------------------------------------------
# Fetch RSS feeds
# ---------------------------------------------------------------------------
def GetRssFromUrl(RssItem):
    NewsFeed = feedparser.parse(RssItem[0])
    DateActivity = ""

    for RssObject in reversed(NewsFeed.entries):
        try:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.published_parsed)
        except:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.updated_parsed)
        
        try:
            TmpObject = FileConfig.get('Rss', RssItem[1])
        except:
            FileConfig.set('Rss', RssItem[1], " = ?")
            TmpObject = FileConfig.get('Rss', RssItem[1])

        if TmpObject.endswith("?"):
            FileConfig.set('Rss', RssItem[1], DateActivity)
        else:
            if TmpObject >= DateActivity:
                continue

        OutputMessage = f"Date: {DateActivity}<br>Source:<b> {RssItem[1]}</b><br>Read more: {RssObject.link}<br>"
        Title = Emoji(RssItem[1]) + " " + RssObject.title

        if RssItem[1] == "VERSION":
            Title = f'🔥 A NEW VERSION IS AVAILABLE: {RssObject.title}'
        
        if options.Debug:
            print(Title + " : " + DateActivity)
        else:
            Send_Teams(webhook_feed, OutputMessage, Title)
            time.sleep(3)
        
        FileConfig.set('Rss', RssItem[1], DateActivity)

    with open(ConfigurationFilePath, 'w') as FileHandle:
        FileConfig.write(FileHandle)

# ---------------------------------------------------------------------------
# Fetch Red Flag Domains 
# ---------------------------------------------------------------------------
def GetRedFlagDomains():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        TmpObject = FileConfig.get('Misc', "redflagdomains")
    except:
        FileConfig.set('Misc', "redflagdomains", yesterday)
        TmpObject = yesterday

    TmpObject = datetime.strptime(TmpObject, '%Y-%m-%d').date()
    today_date = datetime.strptime(today, '%Y-%m-%d').date()

    if TmpObject < today_date:
        url = f"https://red.flag.domains/posts/{today}/"
        try:
            response = urllib.request.urlopen(url)
            soup = BeautifulSoup(response, 'html.parser')
            div = soup.find("div", {"class": "content", "itemprop": "articleBody"})
            OutputMessage = ''.join(re.sub(r"[\[\]]", "", p.get_text()) for p in div.find_all("p"))
            Title = f"🚩 Red Flag Domains for {today}"
            
            FileConfig.set('Misc', "redflagdomains", today)
            if options.Debug:
                print(Title)
                print(OutputMessage)
            else:
                Send_Teams(webhook_feed, OutputMessage.replace('\n', '<br>'), Title)
                time.sleep(3)
        except Exception as e:
            print(f"Error fetching Red Flag Domains: {e}")

    with open(ConfigurationFilePath, 'w') as FileHandle:
        FileConfig.write(FileHandle)

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-q", "--quiet", action="store_true", dest="Quiet", default=False)
    parser.add_option("-D", "--debug", action="store_true", dest="Debug", default=False)
    parser.add_option("-d", "--domain", action="store_true", dest="Domains", default=False)
    parser.add_option("-r", "--reminder", action="store_true", dest="Reminder", default=False)
    (options, args) = parser.parse_args()

    webhook_feed = os.getenv('MSTEAMS_WEBHOOK_FEED')
    webhook_ioc = os.getenv('MSTEAMS_WEBHOOK_IOC')
    ConfigurationFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Config.txt')

    if sys.version_info < (3, 10):
        sys.exit("Please use Python 3.10+")
    if webhook_feed is None and not options.Debug:
        sys.exit("Please use a MSTEAMS_WEBHOOK_FEED variable")
    if webhook_ioc is None and not options.Debug:
        sys.exit("Please use a MSTEAMS_WEBHOOK_IOC variable")
    
    if not exists(ConfigurationFilePath):
        sys.exit("Please add Config.txt")
    if not exists("Feed.csv"):
        sys.exit("Please add Feed.csv")
    
    FileConfig = ConfigParser()
    FileConfig.read(ConfigurationFilePath)
    
    GetRssFromUrl(RssFeedList)
    if options.Domains:
        GetRedFlagDomains()
