#!/usr/bin/env python3  
# -*- coding: utf-8 -*- 

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
# Function to send MS-Teams card 
# ---------------------------------------------------------------------------
def Send_Teams(webhook_url:str, content:str, title:str, color:str="000000") -> int:
    """
    Sends a Teams notification.
    """
    response = requests.post(
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        json={
            "themeColor": color,
            "summary": title,
            "sections": [{"activityTitle": title, "activitySubtitle": content}],
        },
    )
    print(f"[DEBUG] Teams Webhook Response: {response.status_code}, {response.text}")
    return response.status_code  # Should be 200

# ---------------------------------------------------------------------------
# Function to fetch RSS feeds  
# ---------------------------------------------------------------------------
def GetRssFromUrl(RssItem):
    print(f"[DEBUG] Fetching RSS Feed from: {RssItem[0]}")
    NewsFeed = feedparser.parse(RssItem[0])
    
    if not NewsFeed.entries:
        print(f"[WARNING] No RSS entries found for {RssItem[1]}. Check if the feed URL is correct.")
        return

    for RssObject in reversed(NewsFeed.entries):
        try:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.published_parsed)
        except:
            DateActivity = time.strftime('%Y-%m-%dT%H:%M:%S', RssObject.updated_parsed)
        
        print(f"[INFO] Processing RSS Entry: {RssObject.title} ({DateActivity})")

        OutputMessage = f"Date: {DateActivity}<br>Source:<b> {RssItem[1]}</b><br>Read more: {RssObject.link}<br>"
        Title = f"📢 {RssObject.title}"

        if options.Debug:
            print(f"[DEBUG] {Title} : {RssObject.title} ({DateActivity})")
        else:
            Send_Teams(webhook_feed, OutputMessage, Title)
            time.sleep(3)

# ---------------------------------------------------------------------------
# Main Execution   
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [options]", version="%prog 2.2.0")
    parser.add_option("-D", "--debug", action="store_true", dest="Debug", default=False, help="Debug mode")
    (options, args) = parser.parse_args()

    # Get Microsoft Teams Webhook from environment variables
    webhook_feed = os.getenv('MSTEAMS_WEBHOOK_FEED')
    webhook_ioc = os.getenv('MSTEAMS_WEBHOOK_IOC')

    print(f"[DEBUG] Webhook Feed URL: {webhook_feed}")
    print(f"[DEBUG] Webhook IOC URL: {webhook_ioc}")

    if not webhook_feed:
        sys.exit("[ERROR] MSTEAMS_WEBHOOK_FEED is not set. Check GitHub Actions Secrets.")
    if not webhook_ioc:
        sys.exit("[ERROR] MSTEAMS_WEBHOOK_IOC is not set. Check GitHub Actions Secrets.")

    ConfigurationFilePath = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'Config.txt')

    if not exists(ConfigurationFilePath):
        sys.exit("[ERROR] Config.txt file is missing!")
    if not exists("./Feed.csv"):
        sys.exit("[ERROR] Feed.csv file is missing!")

    # Read the Config.txt file   
    FileConfig = ConfigParser()
    FileConfig.read(ConfigurationFilePath)

    with open('Feed.csv', newline='') as f:
        reader = csv.reader(f)
        RssFeedList = list(reader)
    
    for RssItem in RssFeedList:
        if '#' in str(RssItem[0]):
            continue
        GetRssFromUrl(RssItem)
