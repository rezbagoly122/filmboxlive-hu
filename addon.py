# -*- coding: utf-8 -*-
import sys
import requests
import json
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import inputstreamhelper
########################
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
######################################

is_py2 = sys.version_info[0] == 2
is_py3 = sys.version_info[0] == 3

if is_py2:
    from urlparse import parse_qsl
    import urllib
    unicode = unicode
    basestring = basestring

elif is_py3:
    from urllib.parse import parse_qsl
    import urllib.request
    import urllib.parse
    import urllib.error
    str = unicode = basestring = str

# f = open('lista.txt','w') # loghoz
######################################
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.filmboxlivehu')
resources = xbmc.translatePath(addon.getAddonInfo('path') + '/resources/')
main_url = 'http://filmboxliveapp.net/cmsendpoint.json'
api_url = 'https://api.invideous.com'
channels_url = 'http://www.filmboxliveapp.net/channel/'
##############################################################################
country_check_url = 'http://mip.filmboxlive.com/CountryService.svc/CheckCountry'
ticket_url = 'http://key.erstream.com/api/ticket/create'

username = addon.getSetting('username')
password = addon.getSetting('password')
sessionid = params.get('sessionid', '')
userid = params.get('userid', '')

#f = open('lista.txt', 'w')

repeated = False

MUA = 'Dalvik/2.1.0 (Linux; U; Android 5.1; Dalvik/2.1.0 (Linux; U; Android 8.0.0; Nexus 5X Build/OPP3.170518.006) Build/LMY47D)'

publisher_id = '25131'
package_id = '120'
ticket_key = '5dd3e0da5423de187d9938a45e2c81b7'


def build_url(query):
    if is_py2:
        return base_url + '?' + urllib.urlencode(query)
    else:
        return base_url + '?' + urllib.parse.urlencode(query)


def add_item(name, image, is_folder, is_playble, payload, info_labels={}):

    list_item = xbmcgui.ListItem(label=name)

    if is_playble:
        list_item.setProperty("IsPlayable", 'true')
    else:
        list_item.setProperty("IsPlayable", 'false')

    info_labels['title'] = name
    info_labels['sorttitle'] = name

    payload['sessionid'] = sessionid
    payload['userid'] = userid

    list_item.setInfo(type='video', infoLabels=info_labels)
    list_item.setArt({'thumb': image, 'poster': image,
                      'banner': image, 'fanart': image})

    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url=url,
        listitem=list_item,
        isFolder=is_folder
    )


def add_folder(name, image, payload):
    add_item(name, image, True, False, payload)


def LiveTV():
    response = requests.get(channels_url + 'channels_hun.json').text
    channels = json.loads(response)
    for channel in channels['channels']:
        name = channel['name']
        if name == 'FilmBox Basic':
            name = 'FilmBox'
        url = channel['stream']
        image = channels_url + channel['images'][0]['image']
        folder = False
        playble = True
        mode = 'play'
        add_item(name, image, folder, playble, {'mode': mode, 'url': url})
    xbmcplugin.endOfDirectory(addon_handle)


def play():

    url = params.get('url', None)
#    f.write(str(url))
    if 'm3u8' not in url and 'mp4' not in url:
        final_url = requests.get(
            url,
            verify=False,
            allow_redirects=False,
            headers={'User-Agent': MUA, 'Referer': api_url}
        ).headers.get('Location', None)
    else:
        final_url = url
    country_response = requests.get(
        country_check_url,
        verify=False,
        headers={'User-Agent': MUA}
    ).json()
    ip = country_response.get('ClientIP', None)
    if final_url:
        data = {
            'url': final_url,
            'clientip': ip,
            'key': ticket_key,
            'userid': userid,
            'device': 'Google',
            'domain': 'Filmbox'
        }
        response = requests.get(
            ticket_url,
            params=data,
            verify=False,
            headers={'User-Agent': MUA, 'Referer': url}
        ).text
        manifest = final_url + '?' + response + \
            '&device=Google&userID='+userid+'&domain=filmbox'
#        f.write(str(manifest))
        if 'mp4' in final_url:
            play_item = xbmcgui.ListItem(path=manifest)
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
            return
        is_helper = inputstreamhelper.Helper('hls')
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=manifest)
            play_item.setProperty('inputstreamaddon',
                                  is_helper.inputstream_addon)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:
        print('no final')


def login():
    global sessionid
    global userid
    global repeated
    username = addon.getSetting('username')
    password = addon.getSetting('password')
    if not username or not password:
        xbmcgui.Dialog().ok('Filmbox Live',
                        'Add meg a felhasználói azonosítót a beállításokban.')
        addon.openSettings()
        return login()
    data = {
        'username': username,
        'password': password,
        'platform': 'mobile'
    }
    response = requests.post(
        api_url + '/plugin/login',
        params=data,
        verify=False,
        headers={'User-Agent': MUA}
    ).json()
    user_info = response.get('response', {}).get(
        'result', {}).get('user_info', {})
    if user_info.get('guest', '1') == '0':
        sessionid = user_info.get('session_id', None)
        userid = user_info.get('id', None)
        return True
    else:
        if not repeated:
            repeated = True
            return login()
        else:
            sessionid = ''
            userid = ''
            xbmcgui.Dialog().ok('Sikertelen bejelentkezés.',
                                'Ellenőrizze a felhasználónevet és a jelszót',
                                 'és az előfizetés érvényességét.')
        return False


def list(search_phrase=None):

    search_name = params.get('searchName', None)
    page = params.get('page', '1')
    id = params.get('id', None)
    season = params.get('season', None)
    data = {
        'publisher_id': publisher_id,
        'package_id': package_id,
        'records_per_page': '50'
    }
    if search_phrase:
        data['custom_filter_by_title'] = search_phrase
    elif search_name:
        xbmcplugin.setContent(addon_handle, 'movies')
        data['custom_filter_by_genre'] = search_name
        data['custom_order_by_order_priority'] = 'asc'
        data['page'] = page
    else:
        xbmcplugin.setContent(addon_handle, 'episodes')
        data['custom_filter_by_series_id'] = id
        data['custom_filter_by_season_num'] = season
        data['custom_order_by_episode_code'] = ''
        data['page'] = page
    response = requests.get(
        api_url + '/plugin/get_package_videos',
        params=data,
        verify=False,
        headers={'User-Agent': MUA}
    ).json()
    videos = response.get('response', {}).get('result', {}).get('videos', [])
    for video in videos:
        id = video.get('id', None)
        attributes = video.get('custom_attributes', {})
        title = video.get('title', '').encode('utf-8', 'ignore')
        image = attributes.get('promoImage', '')
        genre = attributes.get('genres_hu', '').encode('utf-8', 'ignore')
        info_labels = prepare_info_labels(attributes)
        ##############
        if title == 'CASSANDRE HD':
            add_item('CASSANDRE', image, True, False, {
                     'mode': 'list', 'searchName': 'CASSANDRE'}, info_labels)
            continue
        if title == 'VEUM':
            add_item('VEUM', image, True, False, {
                     'mode': 'list', 'searchName': 'VEUM'}, info_labels)
            continue
        if title == 'FARKAS-PATAK HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'WOLF1'}, info_labels)
            continue
        if title == 'EINSTEIN REJTÉLYEI HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'EINSTEIN1'}, info_labels)
            continue
        if title == 'CSIKORGÓ ACÉL HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'METAL1'}, info_labels)
            continue
        if title == 'BÁRÓK ÉS DÍLEREK HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'CARTEL1'}, info_labels)
            continue
        if title == 'GYILKOS NAP HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'SUN1'}, info_labels)
            continue
        if title == 'SZÖRNYETEG HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'MONSTER1'}, info_labels)
            continue
        if title == 'BŰN ÉS ÁRTATLANSÁG HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'INNICENT1'}, info_labels)
            continue
        if title == 'MÓDUSZ HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'MODUS1'}, info_labels)
            continue
        if title == 'A MÓKA KEDVÉÉRT HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'FORFUN1'}, info_labels)
            continue
        if title == 'ÁLOMUTAZÁS HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'JOURNEY1'}, info_labels)
            continue
        if title == 'ÍGY KÉSZÜL HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'MADE1'}, info_labels)
            continue
        if title == 'MUMU TRIBE HD':
            add_item(title, image, True, False, {
                     'mode': 'list', 'searchName': 'MUMU1'}, info_labels)
            continue
        ##############
        else:
            url = attributes.get('ios_source_url', None)
        seasons = attributes.get('available_season', None)
        if seasons:
            mode = 'seasons'
            playble = False
            folder = True
        else:
            mode = 'play'
            playble = True
            folder = False
        add_item(title, image, folder, playble, {
                 'mode': mode, 'url': url, 'seasons': seasons, 'id': id}, info_labels)
    total = response.get('response', {}).get(
        'result', {}).get('total_pages', 0)
    next = int(page) + 1
    if next <= total:
        ##########################
        add_folder('[B]Ugrás a(z) '+str(int(next))+'. oldalra >> Összes oldal:'+str(int(total))+'[/B]',
                   resources+'Kovetkezo.png', {'mode': 'list', 'page': str(next), 'searchName': search_name})
        ##########################
    if search_phrase and len(videos) == 0:
        add_folder('Vissza, nincs találat.', resources + 'Elozo.png', {})
    xbmcplugin.endOfDirectory(addon_handle)


def prepare_info_labels(attributes):
    ##########################
    genres = attributes.get('genres_hu', '')
    ##########################
    genres = [x.replace('1', '').replace('2', '').replace('3', '')
              for x in genres]

    components = attributes.get('duration', '').split(":")
    duration = ''
    if len(components) > 1:
        duration = (int(components[0]) * 3600) + (int(components[1]) * 60)
    if len(components) > 2:
        duration = duration + int(components[0])
    return {
        ########################
        'plot': attributes.get('description_hu', ''),
        ########################
        'duration': duration,
        'genre': genres,
        'country': attributes.get('country', '').split(','),
        'year': attributes.get('year_of_production', ''),
#        'cast': attributes.get('cast', '').split(','),
        'director': attributes.get('director', '').split(','),
        'mpaa': attributes.get('age_raiting', ''),
        'originaltitle': attributes.get('title_en', ''),
    }


def seasons():
    xbmcplugin.setContent(int(sys.argv[1]), 'season')
    id = params.get('id', None)
    seasons = params.get('seasons', '1').split(',')
    for season in seasons:
        add_folder('Évad ' + season, '',
                   {'mode': 'list', 'id': id, 'season': season})
    xbmcplugin.endOfDirectory(addon_handle)


def movies():
    response = requests.get(
        main_url,
        verify=False,
        headers={'User-Agent': MUA}
    ).json()
    cms_endpoint = response.get('cmsendpoint', None) + '/getAllCategories'
    categories = requests.get(
        cms_endpoint,
        ###################
        params={'countryName': 'hu'},
        ###################
        verify=False,
        headers={'User-Agent': MUA}
    ).json()
    for category in categories:
        name = category.get('name', '')
        search_name = category.get('searchName', '')
        add_item(name, '', True, False, {
                 'mode': 'list', 'searchName': search_name})
###################
#    add_item('Erox', '', True, False, {'mode': 'list', 'searchName': 'EROX1'})
###################
    xbmcplugin.endOfDirectory(addon_handle)


def search():
    keyb = xbmc.Keyboard('', 'Filmek, sorozatok keresése...')
    keyb.doModal()
    if (keyb.isConfirmed()):
        if keyb.getText() == '':
            add_folder('Vissza, nincs találat.', resources + 'back.png', {})
            xbmcplugin.endOfDirectory(addon_handle)
        else:
            list(keyb.getText())


def home():
    if not userid:
        if not login():
            return
    add_folder('Filmek, sorozatok keresése...',
               resources + 'search.png', {'mode': 'search'})
    add_folder('Filmek', '', {'mode': 'movies'})
    add_folder('Sorozatok', '', {'mode': 'list', 'searchName': 'SERIES1'})
    add_folder('Élő adások', '', {'mode': 'LiveTV'})


if __name__ == '__main__':
    mode = params.get('mode', None)
    if not mode:
        home()
    elif mode == 'movies':
        movies()
    elif mode == 'LiveTV':
        LiveTV()
    elif mode == 'seasons':
        seasons()
    elif mode == 'list':
        list()
    elif mode == 'play':
        play()
    elif mode == 'search':
        search()
