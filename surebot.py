# -*- coding: utf-8 -*-


import os
import sys
import time
import json
import urllib.parse
import random
import datetime
import atexit
import math
import requests

class SureBot:

    # consts
    FOLLOWERS = 'followers'
    FOLLOWING = 'following'
    MEDIA = 'media'
    SIMILAR = 'similar'
    LIKES = 'likes'
    FOLLOWS = 'follows'
    UNFOLLOWS = 'unfollows'
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
        'media': 'https://www.instagram.com/p/{0}/?__a=1',
        'url_likes': 'https://www.instagram.com/web/likes/{0}/like/',
        'url_comment': 'https://www.instagram.com/web/comments/{0}/add/',
        'url_follow': 'https://www.instagram.com/web/friendships/{0}/follow/',
        'url_unfollow': 'https://www.instagram.com/web/friendships/{0}/unfollow/',
        'url_login': 'https://www.instagram.com/accounts/login/ajax/',
        'url_logout': 'https://www.instagram.com/accounts/logout/'
    }
    __STATS = {
        LIKES: [],
        FOLLOWS: [],
        COMMENTS: [],
        UNFOLLOWS: []
    }
    # the blacklist is where everyone we've interacted with goes
    __BLACKLIST = []
    __UNFOLLOW_CURSOR = 0
    __LIKED = 0
    __FOLLOWED = 0
    __UNFOLLOWED = 0
    __COMMENTED = 0
    # browser things
    user_agent = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36")
    accept_language = 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4'

    def __init__(self, username='', password=''):
        print("👀 SureBot reporting for duty! {}\n".format(datetime.datetime.now().strftime("%d-%m-%Y %H:%M")))
        # options
        self.start_time = datetime.datetime.now()
        self.username = username
        self.user_key = password
        self.my_profile = None

        # session
        self.s = requests.Session()
        self.login_status = False

        # at exit
        atexit.register(self.die)

        # attempt login
        self.login()
        if self.login_status != True:
            print('Login failed')
            self.die()

    def login(self):
        print('Trying to login as {}...\n'.format(self.username))
        self.s.cookies.update({
            'sessionid': '',
            'mid': '',
            'ig_pr': '1',
            'ig_vw': '1920',
            'csrftoken': '',
            's_network': '',
            'ds_user_id': ''
        })
        self.login_params = {
            'username': self.username,
            'password': self.user_key
        }
        self.s.headers.update({
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': self.accept_language,
            'Connection': 'keep-alive',
            'Content-Length': '0',
            'Host': 'www.instagram.com',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
            'User-Agent': self.user_agent,
            'X-Instagram-AJAX': '1',
            'X-Requested-With': 'XMLHttpRequest'
        })
        r = self.s.get(self.ENDPOINTS['insta_home'])
        self.s.headers.update({'X-CSRFToken': r.cookies['csrftoken']})
        self.__sleep()
        
        login = self.s.post(self.ENDPOINTS['url_login'], data=self.login_params, allow_redirects=True)
        self.s.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
        self.csrftoken = login.cookies['csrftoken']
        self.__sleep()

        if login.status_code == 200:
            r = self.s.get(self.ENDPOINTS['insta_home'])
            finder = r.text.find(self.username)
            if finder != -1:
                self.login_status = True
                print('{} login success!'.format(self.username))
            else:
                self.login_status = False
                print('Login error! Check your login data!')
        else:
            print('Login error! Connection error!')

    # kill the bot
    def die(self):
        unfollow_first = SureBot.__UNFOLLOW_CURSOR < len(
            self.__STATS[SureBot.FOLLOWS])
        if unfollow_first:
            print('\nPrepping to die, but first... I\'m trying to unfollow people 😜\n')
            while unfollow_first:
                self.try_unfollow()
                unfollow_first = SureBot.__UNFOLLOW_CURSOR < len(
                    self.__STATS[SureBot.FOLLOWS])
                self.__sleep()

        running_time = datetime.datetime.now() - self.start_time
        print('\nSureBot out 😎\n-----------------')
        print('Running time: {0}\nTotal likes: {1}\nTotal follows: {2}\nTotal unfollows: {3}\nTotal comments: {4}\n'.format(
            running_time, SureBot.__LIKED,
            SureBot.__FOLLOWED,
            SureBot.__UNFOLLOWED,
            SureBot.__COMMENTED))
        
    # get user's profile
    def get_user_profile(self, username, silent=False):
        self.__sleep()
        if not silent:
            print("GET USER PROFILE @{0}".format(username))
        response = self.s.get(
            SureBot.ENDPOINTS['user_profile'].format(username))
        if response.status_code != 200:
            if not silent:
                print("User '{0}' not found: {1}".format(
                    username, response.status_code))
            return None

        return json.loads(response.text)['user']

    # get user's followers
    def get_user_followers(self, username, max_followers=20):
        '''
        when max_followers is <= 0, means unlimited
        '''
        self.__sleep()
        print("GET USER FOLLOWERS @{0}".format(username))
        user = self.get_user_profile(username, True)
        if not self.__can_interact(user):
            print("@{0} not found, or is a private account, or they've blocked you!".format(
                username))
            return
        current_user_followers = []
        end_cursor = None
        has_next = True

        while (len(current_user_followers) < max_followers and has_next) or (has_next and max_followers <= 0):
            self.__sleep()
            params = {'id': user['id'], 'first': 5}
            if end_cursor:
                params['after'] = end_cursor
                # params['first'] = 10

            response = self.s.get(self.__build_query(params))
            if response.status_code != 200:
                print("Followers for @{} could not be fetched: {} ({})".format(
                    username, response.status_code, response.text))
                return

            data = json.loads(response.text)
            if data['status'] != 'ok':
                print(
                    "Unable to fetch followers for @{0}".format(username))
                return

            data = data['data']
            if data['user']['edge_followed_by']['count'] == 0:
                print("@{0} has no followers".format(username))
                return

            # go on with this user
            has_next = data['user']['edge_followed_by']['page_info']['has_next_page']
            end_cursor = data['user']['edge_followed_by']['page_info']['end_cursor']

            filtered = self.__filter_followers(
                data['user']['edge_followed_by']['edges'])
            current_user_followers += filtered if filtered else []
            current_user_followers = current_user_followers[:
                                                            max_followers] if max_followers > 0 else current_user_followers

            print("Fetched '{0}' of {1} follower(s)\n".format(
                len(current_user_followers), data['user']['edge_followed_by']['count']))

        return current_user_followers

    # get user's feed
    def get_user_feed(self, username, max_media_count=20):
        '''
        when max_media_count is <= 0, means unlimited
        '''
        self.__sleep()
        print("Getting feed for \t", username)
        user = self.get_user_profile(username, True)
        if not self.__can_interact(user):
            print("@{0} not found, or is a private account, or they've blocked you!".format(
                username))
            return

        current_user_media = []
        end_cursor = None
        has_next = True

        while (len(current_user_media) < max_media_count and has_next) or (has_next and max_media_count <= 0):
            self.__sleep()
            params = {'id': user['id'], 'first': 5}
            if end_cursor:
                params['after'] = end_cursor

            query = self.__build_query(params, SureBot.MEDIA)
            response = self.s.get(query)
            if response.status_code != 200:
                print("Media feed for @{} could not be fetched: {} ({})".format(
                    username, response.status_code, response.text))
                return

            data = json.loads(response.text)
            if data['status'] != 'ok':
                print("Unable to fetch media feed for @{0}".format(username))
                return

            data = data['data']
            if data['user']['edge_owner_to_timeline_media']['count'] == 0:
                print("@{0} has no media uploaded".format(username))
                return

            # go on with this media feed
            has_next = data['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
            end_cursor = data['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']

            # pick em media
            filtered = self.__filter_media(
                data['user']['edge_owner_to_timeline_media']['edges'])
            current_user_media += filtered if filtered else []
            current_user_media = current_user_media[:
                                                    max_media_count] if max_media_count > 0 else current_user_media

            print("Fetched '{0}' of {1} media\n".format(len(current_user_media),
                                                        data['user']['edge_owner_to_timeline_media']['count']))

        return current_user_media

    # likes a feed of media
    def feed_liker(self, feed):
        if not feed:
            print('Cannot like empty feed!')
            return

        for media in feed:
            self.__sleep()
            self.like(media)

    # perform a like operation
    def like(self, media):
        if not self.safe_limits(SureBot.LIKES):
            print('Likes limit reached for the day')
            return

        """ Send http request to like media by ID """
        if self.login_status:
            print('Liking a {0}: #{1}'.format(
                media['media_type'], SureBot.__LIKED + 1))
            url_likes = self.ENDPOINTS['url_likes'].format(media['media_id'])
            try:
                like = self.s.post(url_likes)
                self.__STATS[SureBot.LIKES].append(media)
                SureBot.__LIKED += 1
            except Exception as e:
                print("Like operation failed! {0}".format(e.message))
                like = 0
            return like

    # follow a user
    def follow(self, user):
        if not self.safe_limits(SureBot.FOLLOWS):
            print('Follows limit reached for the day')
            return

        """ Send http request to follow """
        if self.login_status:
            print('Trying to follow @{0}: #{1}'.format(
                user['username'], SureBot.__FOLLOWED + 1))
            u = self.get_user_profile(user['username'], True)
            if not self.__can_follow(u):
                print("Cannot follow @{0}".format(user['username']))
                return False

            url_follow = self.ENDPOINTS['url_follow'].format(user['user_id'])
            try:
                self.__sleep()
                follow = self.s.post(url_follow)
                if follow.status_code == 200:
                    user['unfollow_at'] = self.__offset_time(1 * 60)[0]
                    self.__STATS[SureBot.FOLLOWS].append(user)
                    SureBot.__FOLLOWED += 1
                return follow
            except Exception as e:
                print("Unable to follow! {0}".format(e.message))
        return False

    # get information about a media item
    def get_media_info(self, media_code, silent=True):
        self.__sleep()
        if not silent:
            print("Getting media info for \t", media_code)
        response = self.s.get(
            SureBot.ENDPOINTS['media'].format(media_code))
        if response.status_code != 200:
            print("Media not found: {0}".format(response.status_code))
            return None

        return json.loads(response.text)

    # checks that bot is still within safe operation limits
    def safe_limits(self, which):
        return len(self.__STATS[which]) < SureBot.LIMITS[which]

    # unfollow routine
    def try_unfollow(self):
        if SureBot.__UNFOLLOW_CURSOR >= len(self.__STATS[SureBot.FOLLOWS]):
            return
        current_user = dict(
            self.__STATS[SureBot.FOLLOWS][SureBot.__UNFOLLOW_CURSOR])
        if time.time() < current_user['unfollow_at']:
            return
        if not self.unfollow(current_user) and 'failed' not in current_user:
            current_user['failed'] = True
            retry = self.__offset_time(random.choice(list(range(15, 30))))
            current_user['unfollow_at'] = retry[0]
            print('Will retry in {0} secs'.format(retry[1]))
        else:
            SureBot.__UNFOLLOW_CURSOR += 1
            SureBot.__UNFOLLOWED += 1
            if (SureBot.__UNFOLLOW_CURSOR < len(self.__STATS[SureBot.FOLLOWS])):
                nxt = self.__offset_time(random.choice(list(range(15, 30))))
                nxt_user = dict(
                    self.__STATS[SureBot.FOLLOWS][SureBot.__UNFOLLOW_CURSOR])
                if time.time() <= nxt_user['unfollow_at']:
                    nxt_user['unfollow_at'] = nxt[0]

    # unfollows a user
    def unfollow(self, user):
        """ Send http request to unfollow """
        if self.login_status:
            print('Unfollowing @{0}: #{1}'.format(
                user['username'], SureBot.__UNFOLLOWED + 1))
            url_unfollow = self.ENDPOINTS['url_unfollow'].format(user['user_id'])
            try:
                unfollow = self.s.post(url_unfollow)
                if unfollow.status_code == 200:
                    self.__STATS[SureBot.UNFOLLOWS].append(user)
                else:
                    print("Unable to unfollow!")
                    return False
                return True
            except Exception as e:
                print("Unable to unfollow! {0}".format(e.message))
        return False

    # interact with user's followers
    def interact(self, username, max_likes=5, max_followers=5, follow_rate=.1, comment_rate=.1, depth=0):
        print("\nInteracting with @{0}".format(username))
        user = self.get_user_profile(username)
        if not self.__can_interact(user):
            print("Interaction impossible for @{0}".format(username))
            return
        user_feed = self.get_user_feed(username, max_likes)
        self.feed_liker(user_feed)
        # think of it as type casting
        user = {'username': user['username'], 'user_id': user['id']}
        self.follow(user)

        followers = self.get_user_followers(username, max_followers)
        if not followers:
            return

        # calculate follow_rate
        follow_index = self.__to_follow(follow_rate, len(followers))
        for index, follower in enumerate(followers):
            if depth > 0:
                self.__sleep(True)
                self.interact(follower['username'], max_likes,
                              max_followers, follow_rate, comment_rate, depth - 1)
                # recursion above, do the digging!
            else:
                if follower['username'] in SureBot.__BLACKLIST:
                    print("Interacted with @{0} already, skipping...".format(
                        follower['username']))
                    return

                feed = self.get_user_feed(follower['username'], max_likes)
                self.feed_liker(feed)
                if (index < follow_index):
                    self.follow(follower)
                self.try_unfollow()
                SureBot.__BLACKLIST.append(follower['username'])
            print('\n')

    # Privates ----------

    # filter followers stream based on certain criteria
    def __filter_followers(self, followers):
        useful = []
        for follower in followers:
            user = self.get_user_profile(follower['node']['username'], True)
            if not self.__can_interact(user):
                print("@{0} not found, or is a private account, or they've blocked you!".format(
                    follower['node']['username']))
                continue

            if user['follows_viewer'] or user['has_requested_viewer']:
                print("Skipping @{0}, they follow you already".format(
                    user['username']))
                continue
            if user['username'] == self.username:
                print("Skipping your own account")
                continue
            useful.append(
                {'username': user['username'], 'user_id': user['id']})
        random.shuffle(useful)
        return useful

    # filter media stream based on certain criteria
    def __filter_media(self, media):
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

    def __build_query(self, params, query=FOLLOWERS):
        url = urllib.parse.urlencode({"variables": json.dumps(params)})
        # url = data.encode('utf-8')
        return '{3}{0}?query_id={1}&{2}'.format(SureBot.ENDPOINTS['graphql'],
                                                SureBot.QUERY_IDS[query], url,
                                                SureBot.ENDPOINTS['insta_home'])

    # random time sleeper
    def __sleep(self, more=False):
        s = random.choice(range(1, 4) if not more else range(5, 15))
        time.sleep(s)

    # adds offset seconds to time, plus random offset
    def __offset_time(self, offset=0):
        offset += random.choice(list(range(0, 15)))
        return int(time.time()) + offset, offset

    # determine if this person can be followed
    def __can_follow(self, user):
        return not user['requested_by_viewer'] and not user['followed_by_viewer'] and not user['username'] == self.username and not user['has_blocked_viewer']

    # determine if this user is one we can interact with
    def __can_interact(self, user):
        return not (not user or user['is_private'] or user['has_blocked_viewer'])

    # determines how many people to follow
    def __to_follow(self, rate, popu):
        i = int(math.floor(rate * popu))
        return i if i > 0 else 1
