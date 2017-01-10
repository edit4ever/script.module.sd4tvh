from subprocess import Popen
from xbmcswift2 import Plugin
import StringIO
import os
import re
import requests
import sys
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcplugin
import zipfile
import operator
import HTMLParser
from sdAPI import SdAPI
import hashlib
import datetime,time
from utils import *
import sqlite3
import cgi

plugin = Plugin()

def log(v):
    xbmc.log(repr(v))


def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

@plugin.route('/add_provider')
def add_provider():
    user = plugin.get_setting('User')
    passw = plugin.get_setting('Pass')
    passw = hashlib.sha1(passw.encode('utf-8')).hexdigest()
    sd = SdAPI(user=user, passw=passw)
    if not sd.logged_in:
        #TODO popup settings
        return
    #global sd
    status = 'You have %d / %d lineups' % (len(sd.lineups), sd.max_lineups)
    if sd.max_lineups - len(sd.lineups) < 1:
        xbmcgui.Dialog().ok(
            xbmcaddon.Addon().getAddonInfo('name'), status,
            'To add a new one you need to first remove one of your lineups')
        return

    country_list = sd.get_countries()
    countries = []
    for country in country_list:
        countries.append(country['fullName'])
    countries = sorted(countries, key=lambda s: s.lower())
    sel = xbmcgui.Dialog().select('Select country - %s' % status, list=countries)
    if sel >= 0:
        name = countries[sel]
        sel_country = [x for x in country_list if x["fullName"] == name]
        if len(sel_country) > 0:
            sel_country = sel_country[0]
            keyb = xbmc.Keyboard(sel_country['postalCodeExample'], 'Enter Post Code')
            keyb.doModal()
            if keyb.isConfirmed():
                lineup_list = sd.get_lineups(country=sel_country["shortName"], postcode=keyb.getText())
                lineups = []
                saved_lineups = sd.lineups
                for lineup in lineup_list:
                    if lineup['lineup'] not in saved_lineups:
                        lineups.append(lineup['name'])
                lineups = sorted(lineups, key=lambda s: s.lower())
                sel = xbmcgui.Dialog().select('Select lineup - not showing already selected...',
                                              list=lineups)
                if sel >= 0:
                    name = lineups[sel]
                    sel_lineup = [x for x in lineup_list if x["name"] == name]
                    if len(sel_lineup) > 0:
                        sel_lineup = sel_lineup[0]
                        xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Saving lineup...',
                                                      os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'icon.png'), 3000)
                        if sd.save_lineup(sel_lineup['lineup']):
                            xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'),
                                                          'Lineup "%s" saved' % name,
                                                          os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'icon.png'), 5000)
                        else:
                            raise SourceException('Lineup could not be saved! '
                                                  'Check the log for details.')

@plugin.route('/remove_provider')
def remove_provider():
    user = plugin.get_setting('User')
    passw = plugin.get_setting('Pass')
    passw = hashlib.sha1(passw.encode('utf-8')).hexdigest()
    sd = SdAPI(user=user, passw=passw)
    #global sd, database
    lineup_list = sd.get_user_lineups()
    if len(lineup_list) == 0:
        return
    lineups = []
    for lineup in lineup_list:
        lineups.append(lineup['name'])
    lineups = sorted(lineups, key=lambda s: s.lower())
    sel = xbmcgui.Dialog().select('Current lineups - Click to delete...', list=lineups)
    if sel >= 0:
        name = lineups[sel]
        sel_lineup = [x for x in lineup_list if x["name"] == name]
        if len(sel_lineup) > 0:
            sel_lineup = sel_lineup[0]
            yes_no = xbmcgui.Dialog().yesno(xbmcaddon.Addon().getAddonInfo('name'),
                                            '[COLOR red]Deleting a lineup will also remove all '
                                            'channels associated with it![/COLOR]',
                                            'Do you want to continue?')
            if yes_no:
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Deleting lineup...',
                                              os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'icon.png'), 3000)
                if sd.delete_lineup(sel_lineup['lineup']):
                    #TODO
                    #database.deleteLineup(close, sel_lineup['lineup'])
                    xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Lineup "%s" deleted' % name,
                                                  os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'icon.png'), 5000)


@plugin.route('/')
def index():
    items = []
    items.append(
    {
        'label': 'Add TV Provider',
        'path': plugin.url_for('add_provider'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': 'Remove TV Provider',
        'path': plugin.url_for('remove_provider'),
        'thumbnail':get_icon_path('settings'),
    })
    return items


if __name__ == '__default__':
    plugin.run()
