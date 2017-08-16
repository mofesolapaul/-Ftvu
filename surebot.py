#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

import os
import sys
import time
import json
import urllib
import random
import datetime

sys.path.append(os.path.join(sys.path[0], 'src'))
from instabot import InstaBot


class SureBot:

    # consts
    FOLLOWERS = 'followers'
    FOLLOWING = 'following'
    MEDIA = 'media'
    SIMILAR = 'similar'
    LIKES = 'likes'
    FOLLOWS = 'follows'
    UNFOLLOWS = 'follows'
    COMMENTS = 'comments'

    LIMITS = {
        LIKES: 1000,
        FOLLOWS: 300,
        COMMENTS: 100
    }
    QUERY_IDS = {
        FOLLOWERS: '17851374694183129',
        FOLLOWING: '17874545323001329',
        MEDIA: '17888483320059182',
        SIMILAR: '17845312237175864'
    }
    ENDPOINTS = {
        'insta_home': 'https://www.instagram.com',
        'user_profile': 'https://www.instagram.com/{0}/?__a=1',
        'graphql': '/graphql/query/',
        'media': 'https://www.instagram.com/p/{0}/?__a=1'
    }
    _STATS = {
        LIKES: [],
        FOLLOWS: [],
        COMMENTS: [],
        UNFOLLOWS: []
    }

    def __init__(self, user_name='', password=''):
        # options
        self.start_time = datetime.datetime.now()
        self.user_name = user_name
        self.user_key = password
        self.my_profile = None

        # attempt login
        self.bot = InstaBot(login=self.user_name,
                            password=self.user_key, log_mod=0)
        if self.bot.login_status != True:
            print('Login failed')
            self.die()

    # kill the bot
    def die(self):
        running_time = datetime.datetime.now() - self.start_time
        print('\nSureBot out 😎\n-----------------')
        print('Running time: {0}\nTotal likes: {1}\nTotal follows: {2}\nTotal unfollows: {3}\nTotal comments: {4}\n'.format(
            running_time, len(self._STATS[SureBot.LIKES]),
            len(self._STATS[SureBot.FOLLOWS]),
            len(self._STATS[SureBot.UNFOLLOWS]),
            len(self._STATS[SureBot.COMMENTS])))
        self.bot.cleanup()

    # get user's profile
    def get_user_profile(self, user_name):
        self._sleep()
        print("GET USER PROFILE ", user_name)
        response = self.bot.s.get(
            SureBot.ENDPOINTS['user_profile'].format(user_name))
        if response.status_code != 200:
            print("User '{0}' not found: {1}".format(
                user_name, response.status_code))
            return None

        return json.loads(response.text)

    # get user's followers
    def get_user_followers(self, user_name, max_followers=20):
        '''
        when max_followers is <= 0, means unlimited
        '''
        self._sleep()
        print("GET USER FOLLOWERS ", user_name)
        user = self.get_user_profile(user_name)
        if not user or user['user']['is_private'] or user['user']['has_blocked_viewer']:
            print("User '{0}' not found, or is a private account, or they've blocked you!".format(
                user_name))
            return
        current_user_followers = []
        end_cursor = None
        has_next = True

        while (len(current_user_followers) < max_followers and has_next) or (has_next and max_followers <= 0):
            self._sleep()
            params = {'id': user['user']['id'], 'first': 20}
            if end_cursor:
                params['after'] = end_cursor
                # params['first'] = 10

            response = self.bot.s.get(self._build_query(params))
            if response.status_code != 200:
                print("Followers for '{0}' could not be fetched: {1}".format(
                    user_name, response.status_code))
                return

            data = json.loads(response.text)
            if data['status'] != 'ok':
                print(
                    "Unable to fetch followers for '{0}'".format(user_name))
                return

            data = data['data']
            if data['user']['edge_followed_by']['count'] == 0:
                print("User '{0}' has no followers".format(user_name))
                return

            # go on with this user
            has_next = data['user']['edge_followed_by']['page_info']['has_next_page']
            end_cursor = data['user']['edge_followed_by']['page_info']['end_cursor']

            filtered = self._filter_followers(
                data['user']['edge_followed_by']['edges'])
            current_user_followers += filtered if filtered else []

            print("Fetched '{0}' of {1} follower(s)".format(
                len(current_user_followers), data['user']['edge_followed_by']['count']))

        return current_user_followers[:max_followers] if max_followers > 0 else current_user_followers

    # get user's feed
    def get_user_feed(self, user_name, max_media_count=20):
        '''
        when max_media_count is <= 0, means unlimited
        '''
        self._sleep()
        print("GET USER FEED ", user_name)
        user = self.get_user_profile(user_name)
        if not user or user['user']['is_private'] or user['user']['has_blocked_viewer']:
            print("User '{0}' not found, or is a private account, or they've blocked you!".format(
                user_name))
            return

        current_user_media = []
        end_cursor = None
        has_next = True

        while (len(current_user_media) < max_media_count and has_next) or (has_next and max_media_count <= 0):
            self._sleep()
            params = {'id': user['user']['id'], 'first': 12}
            if end_cursor:
                params['after'] = end_cursor

            response = self.bot.s.get(self._build_query(params, SureBot.MEDIA))
            if response.status_code != 200:
                print("Media feed for '{0}' could not be fetched: {1}".format(
                    user_name, response.status_code))
                return

            data = json.loads(response.text)
            if data['status'] != 'ok':
                print(
                    "Unable to fetch media feed for '{0}'".format(user_name))
                return

            data = data['data']
            if data['user']['edge_owner_to_timeline_media']['count'] == 0:
                print("User '{0}' has no media uploaded".format(user_name))
                return

            # go on with this media feed
            has_next = data['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
            end_cursor = data['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']

            # pick em media
            filtered = self._filter_media(
                data['user']['edge_owner_to_timeline_media']['edges'])
            current_user_media += filtered if filtered else []

            print("Fetched '{0}' of {1} media".format(len(current_user_media),
                                                      data['user']['edge_owner_to_timeline_media']['count']))

        return current_user_media[:max_media_count] if max_media_count > 0 else current_user_media

    # likes a feed of media
    def feed_liker(self, feed):
        if not feed:
            print('Cannot like empty feed!')
            return

        for media in feed:
            self._sleep()
            self.like(media)

    # perform a like operation
    def like(self, media):
        if not self.safe_limits(SureBot.LIKES):
            print('Likes limit reached for the day')
            return

        """ Send http request to like media by ID """
        if self.bot.login_status:
            print('Liking a {0}'.format(media['media_type']))
            url_likes = self.bot.url_likes % (media['media_id'])
            try:
                like = self.bot.s.post(url_likes)
                SureBot._STATS[SureBot.LIKES].append(media)
            except:
                print("Like operation failed!")
                like = 0
            return like

    # follow a user
    def follow(self, user):
        if not self.safe_limits(SureBot.FOLLOWS):
            print('Follows limit reached for the day')
            return

        """ Send http request to follow """
        if self.bot.login_status:
            print('Following @{0}'.format(user['username']))
            url_follow = self.bot.url_follow % (user['user_id'])
            try:
                follow = self.bot.s.post(url_follow)
                if follow.status_code == 200:
                    user['unfollow_at'] = time.time() + (2 * 60)
                    SureBot._STATS[SureBot.FOLLOWS].append(user)
                return follow
            except:
                print("Unable to follow!")
        return False

    # get information about a media item
    def get_media_info(self, media_code):
        self._sleep()
        print("GET MEDIA INFO ", media_code)
        response = self.bot.s.get(
            SureBot.ENDPOINTS['media'].format(media_code))
        if response.status_code != 200:
            print("Media not found: {0}".format(response.status_code))
            return None

        return json.loads(response.text)

    # checks that bot is still within safe operation limits
    def safe_limits(self, which):
        return len(SureBot._STATS[which]) < SureBot.LIMITS[which]

    # interact with user's followers
    def interact(self, user_name, max_likes=5, max_followers=5, follow_rate=.1, comment_rate=.1):
        user_feed = self.get_user_feed(user_name, max_likes)
        self.feed_liker(user_feed)

        followers = self.get_user_followers(user_name, max_followers)
        # calculate follow_rate
        f = follow_rate * len(followers)
        for follower in followers:
            feed = self.get_user_feed(follower['username'], max_likes)
            self.feed_liker(feed)

    # Privates ----------

    # filter followers stream based on certain criteria
    def _filter_followers(self, followers):
        useful = []
        for follower in followers:
            user = self.get_user_profile(follower['node']['username'])
            if not user or user['user']['is_private'] or user['user']['has_blocked_viewer']:
                print("User '{0}' not found, or is a private account, or they've blocked you!".format(
                    follower['node']['username']))
                continue

            user = user['user']
            if user['follows_viewer'] or user['has_requested_viewer']:
                print("Skipping {0}, they follow you already".format(
                    user['username']))
                continue
            useful.append(
                {'username': user['username'], 'user_id': user['id']})
        random.shuffle(useful)
        return useful

    # filter media stream based on certain criteria
    def _filter_media(self, media):
        useful = []
        for medium in media:
            medium = medium['node']
            item = self.get_media_info(medium['shortcode'])
            if not item or item['graphql']['shortcode_media']['viewer_has_liked']:
                print('Skipping media item: either not found or already liked')
                continue
            useful.append({'media_id': medium['id'], 'media_code': medium['shortcode'],
                           'media_type': 'video' if medium['is_video'] else 'photo'})
        return useful

    def _build_query(self, params, query=FOLLOWERS):
        data = urllib.urlencode({"variables": json.dumps(params)})
        url = data.encode('utf-8')
        return '{3}{0}?query_id={1}&{2}'.format(SureBot.ENDPOINTS['graphql'],
                                                SureBot.QUERY_IDS[query], url,
                                                SureBot.ENDPOINTS['insta_home'])

    # random time sleeper
    def _sleep(self):
        s = random.choice(range(1, 4))
        time.sleep(s)
