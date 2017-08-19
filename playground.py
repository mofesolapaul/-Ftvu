import json
import time, random
from surebot import SureBot

# fp = open('config.ini', 'r')
username = 'victor_iyiola'
password = 'vickols95'
bot = SureBot(username, password)

bot.get_user_feed(input('supply a user handle:'), max_media_count=3)
# bot.get_user_feed(input('supply a user handle:'), max_media_count=5)
# bot.follow({'username': input('supply a user handle:'), 'user_id': 3292109915})
# bot.interact(input('supply a user handle:'), max_followers=1, max_likes=1)
# bot.die()
