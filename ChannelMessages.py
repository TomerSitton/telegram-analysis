import configparser
import json
import asyncio
from datetime import date, datetime
from time import sleep
import pandas as pd
import re
from urllib.parse import urlparse
from os import listdir
import csv

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import (GetHistoryRequest)
from telethon.tl.types import (
    PeerChannel,
    Message,
    MessageMediaWebPage,
    MessageMediaPhoto
)

CATEGORIES = ["tools", "blogs","cve", "leak", "web", "windows persistance", "linux persistance", "windows pe", "linux pe"]
COLUMNS = ["Date","Category", "Site Name","URL","Title","Description"]
"""message.media.date, CATEGORY , message.media.site_name, message.media.display_url, message.media.title, message.media.description """

async def main(config):
    global CATEGORIES
    await client.start()
    print("Client Created")
    # Ensure you're authorized
    phone = config['Telegram']['phone']
    if await client.is_user_authorized() == False:
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))

    me = await client.get_me()

    channel_url = config['Telegram']['channel']
    if channel_url.isdigit():
        entity = PeerChannel(int(channel_url))
    else:
        entity = channel_url
    my_channel = await client.get_entity(entity)

    message_id = int(config['Telegram']['message_id'])
   
    while True:
        sleep(5)
        messages = client.iter_messages(entity=my_channel,min_id=message_id,reverse=True)

        if not messages:
            break
        async for message in messages:
            if isinstance(message, Message):
                message_id = message.id
                print("Current Message ID is:", message_id)
                
                if message.message.lower() in ["#" + category.lower() for category in CATEGORIES] and message.reply_to is not None:
                        print("reply to message id: {}".format(message.reply_to.reply_to_msg_id))
                        link_message = await client.get_messages(entity=my_channel, ids=message.reply_to.reply_to_msg_id)
                        if link_message.media is not None:
                            data = extract_message_data(link_message=link_message, hashtag_message=message)
                            dump_data(data)
                config.set('Telegram','message_id',str(message_id))
                with open("config.ini","w") as config_file:
                    config.write(config_file)
   
def extract_message_data(link_message, hashtag_message):
    global CATEGORIES
    URL_EXTRACT_PATTERN = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
    for category in CATEGORIES:
        if hashtag_message.message.lower() == "#" + category.lower():
            message_category = category
            break
    data = dict.fromkeys(COLUMNS)
    data["Date"] = link_message.date.strftime('%Y-%m-%d')
    data["Category"] =  message_category

    media = link_message.media
    if isinstance(media, MessageMediaWebPage):
        data["Site Name"] = media.webpage.site_name
        data["URL"] = media.webpage.display_url
        data["Title"] = media.webpage.title
        data["Description"] = media.webpage.description
    elif isinstance(media, MessageMediaPhoto):
        urls = re.findall(URL_EXTRACT_PATTERN,link_message.message)
        data["Site Name"] = ",".join([urlparse(url).netloc for url in urls])
        data["URL"] = ",".join(urls)
        data["Title"] = link_message.message.split('\n',1)[0]
        data["Description"] = link_message.message.split('\n',1)[1]
    else:
        print("Does not support file type {}".format(type(media)))
    return data

def dump_data(data):
    global COLUMNS
    print(data)
    output_dir = "output"
    files = listdir(output_dir)
    values = ["" if value is None else value for value in data.values()]
    if len(files) == 0:
        file_name = "{}/{}.csv".format(output_dir, datetime.today().strftime('%Y-%m-%d'))
        with open(file_name, 'w', encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            writer.writerows([COLUMNS,values])
    elif len(files) == 1:
        with open("{}/{}".format(output_dir,files[0]), 'a', encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(values)
    else:
        print("Too much files in the output directory!")
        return




if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")
    api_id = config['Telegram']['api_id']
    api_hash = config['Telegram']['api_hash']
    username = config['Telegram']['username']
    client = TelegramClient(username, api_id, api_hash)
    with client:
        client.loop.run_until_complete(main(config))
