#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division
import json
import time, random
from surebot import SureBot

fp = open('config.ini', 'r')
myBot = SureBot(str(fp.readline()).strip(), str(fp.readline()).strip())
fp.close()

myBot.get_user_feed(input('supply a user handle:'), max_media_count=3)
# myBot.get_user_feed(input('supply a user handle:'), max_media_count=5)
# myBot.follow({'username': input('supply a user handle:'), 'user_id': 3292109915})
# myBot.interact(input('supply a user handle:'), max_followers=1, max_likes=1)
# myBot.die()
