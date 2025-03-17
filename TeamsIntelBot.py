#!/usr/bin/env python3  
# -*- coding: utf-8 -*- 
#----------------------------------------------------------------------------
# Created By  : Julien Mousqueton @JMousqueton
# Original By : VX-Underground 
# Created Date: 22/08/2022
# Version     : 3.0.0 (2023-05-15)
# ---------------------------------------------------------------------------

import feedparser
import time, requests
import csv
import sys
import json, hashlib
from configparser import ConfigParser
import os
from os.path import exists
from optparse import OptionParser
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

# ---------------------------------------------------------------------------
# Send MS Teams Notification
# ---------------------------------------------------------------------------
def Send_Teams(webhook_url: str, content: str, title: str, color: str = "000000") -> int:
    response = requests.post(
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        json={
            "themeColor": color,
            "summary": title,
            "sections": [{"activityTitle": title, "activitySubtitle": content}]
        }
    )
    return response.status_code

# ---------------------------------------------------------------------------
# Emoji function for titles
# ---------------------------------------------------------------------------
def Emoji(feed):
    match feed:
        case "Leak-Lookup": return '💧 '
        case "VERSION": return '🔥 '
        case "DataBreaches": return '🕳 '
        case "FR-CERT Alertes" | "FR-CERT Avis": return '🇫🇷 '
        case "EU-ENISA Publications": return '🇪🇺 '
        case "Cyber-News": return '🕵🏻‍♂️ '
        case "Bleeping Computer": return '💻 '
        case "Microsoft Sentinel": return '🔭 '
        case "Hacker News": return '📰 '
        case "Cisco": return '📡 '
        case "Securelist": return '📜 '
        case "ATT": return '📞 '
        case "Google TAG": return '🔬 '
        case "DaVinci Forensics": return '📐 '
        case "VirusBulletin": return '🦠 '
        case "Information Security Magazine": return '🗞 '
        case "US-CERT CISA": return '🇺🇸 '
        case "NCSC": return '🇬🇧 '
        case "SANS": return '🌍 '
        case "malpedia": return '📖 '
        case "Unit42": return '🚓 '
        case "Microsoft Security": return 'Ⓜ️ '
        case "Checkpoint Research": return '🏁 '
        case "Proof Point": return '🧾 '
        case "RedCanary": return '🦆 '
        case "MSRC Security Update": return '🚨 '
        case "CIRCL Luxembourg": return '🇱🇺 '
        case _: return '📢 '

# ---------------------------------------------------------------------------
# Fetch and process RSS feed
# ---------------------------------------------------------------------------
def GetRssFromUrl(RssItem):
    NewsFeed = feedparser.parse(RssItem[0])
    DateActivity = ""

    for RssObject in reversed(NewsFeed.entries):
        try:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.published_parsed)
        except:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.updated_parsed)

        tmpObject = FileConfig.get('Rss', RssItem[1], fallback="?")
        
        if tmpObject.endswith("?"):
            FileConfig.set('Rss', RssItem[1], DateActivity)
        elif tmpObject >= DateActivity:
            continue

        output = f"Date: {DateActivity}<br>Source: <b>{RssItem[1]}</b><br>Read more: {RssObject.link}<br>"
        title = f"{Emoji(RssItem[1])} {RssObject.title}"
        
        if options.Debug:
            print(f"{title} - {output}")
        else:
            Send_Teams(webhook_feed, output, title)
            time.sleep(3)

        FileConfig.set('Rss', RssItem[1], DateActivity)

    with open(ConfigurationFilePath, 'w') as configfile:
        FileConfig.write(configfile)

# ---------------------------------------------------------------------------
# Fetch Red Flag domains
# ---------------------------------------------------------------------------
def GetRedFlagDomains():
    today = datetime.now().date()
    last_checked = FileConfig.get('Misc', 'redflagdomains', fallback=str(today - timedelta(days=1)))
    last_checked_date = datetime.strptime(last_checked, '%Y-%m-%d').date()

    if last_checked_date < today:
        url = f"https://red.flag.domains/posts/{today}/"
        try:
            response = urllib.request.urlopen(url)
            soup = BeautifulSoup(response, 'html.parser')
            content = soup.find("div", class_="content", itemprop="articleBody")
            text_output = re.sub(r"[\[\]]", "", content.get_text())

            title = f"🚩 Red Flag Domains for {today}"
            if options.Debug:
                print(title, text_output)
            else:
                Send_Teams(webhook_feed, text_output.replace('\n', '<br>'), title)
            
            FileConfig.set('Misc', 'redflagdomains', str(today))
        except Exception as e:
            print(f"Error fetching Red Flag domains: {e}")

        with open(ConfigurationFilePath, 'w') as configfile:
            FileConfig.write(configfile)

# ---------------------------------------------------------------------------
# Send monthly reminder
# ---------------------------------------------------------------------------
def SendReminder():
    last_reminder = FileConfig.get('Misc', 'reminder', fallback=str(datetime.now() - timedelta(days=31)))
    last_reminder_date = datetime.strptime(last_reminder, '%Y-%m-%d').date()
    one_month_ago = datetime.now().date() - timedelta(days=31)

    if last_reminder_date < one_month_ago:
        output = "Monthly Feeds Reminder:<br>"
        with open('Feed.csv') as f:
            feeds = csv.reader(f)
            for rss in feeds:
                feed_title = rss[1]
                feed_data = feedparser.parse(rss[0])
                feed_date = feed_data.entries[0].published if feed_data.entries else "Unknown"
                output += f"{Emoji(feed_title)} {feed_title} ({feed_date})<br>"

        FileConfig.set('Misc', 'reminder', str(datetime.now().date()))

        if options.Debug:
            print(output)
        else:
            Send_Teams(webhook_ioc, output, "Monthly Feeds Reminder")

        with open(ConfigurationFilePath, 'w') as configfile:
            FileConfig.write(configfile)

# ---------------------------------------------------------------------------
# Main execution block
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-q", "--quiet", action="store_true", dest="Quiet", default=False)
    parser.add_option("-D", "--debug", action="store_true", dest="Debug", default=False)
    parser.add_option("-d", "--domain", action="store_true", dest="Domains")
    parser.add_option("-r", "--reminder", action="store_true", dest="Reminder")
    (options, args) = parser.parse_args()

    webhook_feed = os.getenv('MSTEAMS_WEBHOOK_FEED')
    webhook_ioc = os.getenv('MSTEAMS_WEBHOOK_IOC')
    ConfigurationFilePath = os.path.join(os.path.dirname(__file__), 'Config.txt')
    
    FileConfig = ConfigParser()
    FileConfig.read(ConfigurationFilePath)

    with open('Feed.csv') as f:
        feeds = csv.reader(f)
        RssFeedList = list(feeds)

    for feed in RssFeedList:
        if feed[0].startswith('#'): continue
        GetRssFromUrl(feed)

    if options.Domains:
        GetRedFlagDomains()
    if options.Reminder:
        SendReminder()
