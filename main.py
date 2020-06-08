# coding=utf-8

import subprocess
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
from utilssd import *
import ConfigParser


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

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def run_sd4tvh_channels():
    # Populate filter.cfg channels with 3 steps:
    # - Create, run, and delete temporary script file "tmp_sd4tvh_channels".
    #
    # Prepare credentials, file paths, etc.
    user  = plugin.get_setting('sd.username')
    pass1 = plugin.get_setting('sd.password')
    sd4tvh_exe = xbmc.translatePath(u"special://home/addons/script.module.sd4tvh/sd4tvh.py")
    script_dir = xbmc.translatePath(u"special://userdata/addon_data/script.module.sd4tvh/")
    script_exe = script_dir + 'tmp_sd4tvh_channels'
    filter_cfg = script_dir + 'filter.cfg'
    command_line = 'python ' + sd4tvh_exe                        \
                 + ' -u "' + user + '"'                          \
                 + ' -p "' + pass1 + '"'                         \
                 + ' --channels --channels-path ' + filter_cfg   \
                 + ' --filter --filter-path ' + filter_cfg       \
                 + ' > sd4tvh.log 2>&1'
    # Create temp shell script file to execute sd4tvh.py with arguments
    with open(script_exe, 'w+') as fp:
        fp.write('#!/bin/sh\n')
        fp.write('# NOTE: Temporary file created by script.module.sd4tvh add-on\n.\n')
        fp.write('#   This file created, invoked, and normally deleted by main.py')
        fp.write('. /etc/profile\n\n')
        fp.write('CD=`pwd`\n')
        fp.write('cd ' + script_dir + '\n\n')
        fp.write(command_line + '\n')
        fp.write('RC=$?\n\n')
        fp.write('cd $CD\n')
        fp.write('exit $RC\n')
        fp.close()
    # Make temp shell script file executable
    os.chmod(script_exe, 0o755)
    # Run temp shell script
    rc = 0
    try:
        subprocess.check_call(script_exe)
    except subprocess.CalledProcessError as e:
        rc = e.returncode
        xbmc.log('[sd4tvh] Script tmp_sd4tvh_channels exited with return code ' + str(rc) + '.', xbmc.LOGNOTICE)
        xbmc.log('[sd4tvh] Check log file: ' + script_dir + 'sd4tvh.log', xbmc.LOGNOTICE)
    # Delete temp shell script under normal execution
    if (rc == 0) and os.path.isfile(script_exe):
        os.unlink(script_exe)
    return rc

@plugin.route('/add_provider')
def add_provider():
    user = plugin.get_setting('sd.username')
    passw = plugin.get_setting('sd.password')
    passw = hashlib.sha1(passw.encode('utf-8')).hexdigest()
    sd = SdAPI(user=user, passw=passw)
    if not sd.logged_in:
        #TODO popup settings
        return
    #global sd
    status = 'You have %d of your %d allowed lineups' % (len(sd.lineups), sd.max_lineups)
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
            keyb = xbmc.Keyboard(sel_country['postalCodeExample'], 'Enter ZIP Code')
            keyb.doModal()
            if keyb.isConfirmed():
                lineup_list = sd.get_lineups(country=sel_country["shortName"], postcode=keyb.getText())
                lineups = []
                location = []
                saved_lineups = sd.lineups
                for lineup in lineup_list:
                    if lineup['lineup'] not in saved_lineups:
                        lineupNameLoc = lineup['name'] + " -- " + lineup['location']
                        lineup['name'] = lineupNameLoc
                        lineups.append(lineupNameLoc)
                lineups = sorted(lineups, key=lambda s: s.lower())
                sel = xbmcgui.Dialog().select('Select Schedules Direct Lineup (not showing already subscribed)',
                                              list=lineups)
                if sel >= 0:
                    name = lineups[sel]
                    sel_lineup = [x for x in lineup_list if x["name"] == name]
                    if len(sel_lineup) > 0:
                        sel_lineup = sel_lineup[0]
                        xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Saving lineup...', get_icon_path('plus'), 3000)
                        if sd.save_lineup(sel_lineup['lineup']):
                            xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'),
                                                          'Lineup "%s" saved' % name, get_icon_path('plus'), 5000)
                        else:
                            raise SourceException('Lineup could not be saved! '
                                                  'Check the log for details.')

@plugin.route('/remove_provider')
def remove_provider():
    user = plugin.get_setting('sd.username')
    passw = plugin.get_setting('sd.password')
    passw = hashlib.sha1(passw.encode('utf-8')).hexdigest()
    sd = SdAPI(user=user, passw=passw)
    #global sd, database
    lineup_list = sd.get_user_lineups()
    if len(lineup_list) == 0:
        return
    lineups = []
    for lineupname in lineup_list:
        lineupNameLoc = lineupname['name'] + " -- " + lineupname['location']
        lineupname['name'] = lineupNameLoc
        lineups.append(lineupNameLoc)
    lineups = sorted(lineups, key=lambda s: s.lower())
    sel = xbmcgui.Dialog().select('Current lineups - Click to delete...', list=lineups)
    if sel >= 0:
        name = lineups[sel]
        sel_lineup = [x for x in lineup_list if x["name"] == name]
        if len(sel_lineup) > 0:
            sel_lineup = sel_lineup[0]
            yes_no = xbmcgui.Dialog().yesno(xbmcaddon.Addon().getAddonInfo('name'),
                                            '[COLOR red]Deleting a lineup will remove all channels associated with it![/COLOR]',
                                            '\nDo you want to continue?')
            if yes_no:
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Deleting lineup...', get_icon_path('minus'), 3000)
                if sd.delete_lineup(sel_lineup['lineup']):
                    xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Lineup "%s" deleted' % name, get_icon_path('minus'), 5000)
                else:
                    raise SourceException('Lineup could not be deleted! '
                                          'Check the log for details.')

@plugin.route('/review_channels')
def review_channels():
    xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Updating channels config file...', get_icon_path('tv'), 3000)
    if run_sd4tvh_channels() != 0:
        xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Failed filter.cfg update.  Check Kodi log.', get_icon_path('tv'), 3000)
    user = plugin.get_setting('sd.username')
    pass1 = plugin.get_setting('sd.password')
    passw = hashlib.sha1(pass1.encode('utf-8')).hexdigest()
    sd = SdAPI(user=user, passw=passw)
    #global sd, database
    lineup_list = sd.get_user_lineups()
    if len(lineup_list) == 0:
        return
    lineups = []
    lineupsn = []
    lineupsl = []
    lineupso = []
    for lineupname in lineup_list:
        lineupsn.append(lineupname['name'])
    for lineuploc in lineup_list:
        lineupsl.append(lineuploc['location'])
    for lineup in lineup_list:
        lineupso.append(lineup['lineup'])
    lineupsnew = zip(lineupsn, lineupsl)
    lineups = [ "%s - %s" % x for x in lineupsnew ]
    sel_line = xbmcgui.Dialog().select('Select Schedules Direct Lineup - Click to Edit Channels...', list=lineups)
    if sel_line >= 0:
        parser = ConfigParser.ConfigParser(allow_no_value=True)
        parser.readfp(open(xbmc.translatePath(u"special://userdata/addon_data/script.module.sd4tvh/filter.cfg")))
        lineup_longname = lineups[sel_line]
        lineup_name = lineupso[sel_line]
        lineup_new = lineup_name + "-new"
        lineup_inc = lineup_name + "-include"
        lineup_exc = lineup_name + "-exclude"
        parser.remove_option(lineup_new, "action")
        check_new = len(parser.options(lineup_new))
        if check_new > 0:
            channel_id_new = parser.items(lineup_new)
            channel_number = ( x[0] for x in channel_id_new )
            channel_numbersub = [re.sub("_\d\d\d\d\d", "", sub) for sub in channel_number]
            channel_name = ( x[1] for x in channel_id_new )
            channels_new = zip(channel_numbersub, channel_name)
            channel_list = [ "%s - %s" % x for x in channels_new ]
            channels = []
            for c in channel_list:
                channels.append(c)
            sel_ch = xbmcgui.Dialog().multiselect('New Channels Found - Click to Select Channels to Include', channels)
            if sel_ch >= 0:
                add_num = str(len(sel_ch))
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Adding ' + add_num + ' new channels to the included lineup...', get_icon_path('plus'), 3000)
                channel_number_sel = parser.options(lineup_new)
                for s in sel_ch:
                    channel_num = channel_number_sel[s]
                    channel_nm = parser.get(lineup_new, channel_num)
                    parser.set(lineup_inc, channel_num, channel_nm)
                    parser.remove_option(lineup_new, channel_num)
                channel_number_sel_new = parser.options(lineup_new)
                for s in channel_number_sel_new:
                    channel_num = "%s" % s
                    channel_nm = parser.get(lineup_new, channel_num)
                    parser.set(lineup_exc, channel_num, channel_nm)
                    parser.remove_option(lineup_new, channel_num)
            parser.set(lineup_new, "action", "include")
            sort_inc = sorted(parser.options(lineup_inc), key=natural_keys)
            parser.add_section('temp-inc')
            for s in sort_inc:
                channel_num_sort_inc = "%s" % s
                channel_nm_sort_inc = parser.get(lineup_inc, channel_num_sort_inc)
                parser.set('temp-inc', channel_num_sort_inc, channel_nm_sort_inc)
                parser.remove_option(lineup_inc, channel_num_sort_inc)
            ret_inc = parser.options('temp-inc')
            for s in ret_inc:
                channel_num_ret_inc = "%s" % s
                channel_nm_ret_inc = parser.get('temp-inc', channel_num_ret_inc)
                parser.set(lineup_inc, channel_num_ret_inc, channel_nm_ret_inc)
                parser.remove_option('temp-inc', channel_num_ret_inc)
            parser.remove_section('temp-inc')
            sort_exc = sorted(parser.options(lineup_exc), key=natural_keys)
            parser.add_section('temp-exc')
            for s in sort_exc:
                channel_num_sort_exc = "%s" % s
                channel_nm_sort_exc = parser.get(lineup_exc, channel_num_sort_exc)
                parser.set('temp-exc', channel_num_sort_exc, channel_nm_sort_exc)
                parser.remove_option(lineup_exc, channel_num_sort_exc)
            ret_exc = parser.options('temp-exc')
            for s in ret_exc:
                channel_num_ret_exc = "%s" % s
                channel_nm_ret_exc = parser.get('temp-exc', channel_num_ret_exc)
                parser.set(lineup_exc, channel_num_ret_exc, channel_nm_ret_exc)
                parser.remove_option('temp-exc', channel_num_ret_exc)
            parser.remove_section('temp-exc')
        check_exc = len(parser.options(lineup_exc))
        if check_exc > 0:
            channel_id_exc = parser.items(lineup_exc)
            channel_number_exc = ( x[0] for x in channel_id_exc )
            channel_number_sub_exc = [re.sub("_\d\d\d\d\d", "", sub) for sub in channel_number_exc]
            channel_name_exc = ( x[1] for x in channel_id_exc )
            channels_exc = zip(channel_number_sub_exc, channel_name_exc)
            channel_list_exc = [ "%s - %s" % x for x in channels_exc ]
            channels_x = []
            for c in channel_list_exc:
                channels_x.append(c)
            sel_ch_exc = xbmcgui.Dialog().multiselect('Excluded Channels List - Click to Select Channels to Include', channels_x)
            if sel_ch_exc >= 0:
                add_num_exc = str(len(sel_ch_exc))
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Moving ' + add_num_exc + ' channels to the included lineup...', get_icon_path('plus'), 3000)
                channel_number_sel_exc = parser.options(lineup_exc)
                for s in sel_ch_exc:
                    channel_num_exc = channel_number_sel_exc[s]
                    channel_nm_exc = parser.get(lineup_exc, channel_num_exc)
                    parser.set(lineup_inc, channel_num_exc, channel_nm_exc)
                    parser.remove_option(lineup_exc, channel_num_exc)
            sort_inc = sorted(parser.options(lineup_inc), key=natural_keys)
            parser.add_section('temp-inc')
            for s in sort_inc:
                channel_num_sort_inc = "%s" % s
                channel_nm_sort_inc = parser.get(lineup_inc, channel_num_sort_inc)
                parser.set('temp-inc', channel_num_sort_inc, channel_nm_sort_inc)
                parser.remove_option(lineup_inc, channel_num_sort_inc)
            ret_inc = parser.options('temp-inc')
            for s in ret_inc:
                channel_num_ret_inc = "%s" % s
                channel_nm_ret_inc = parser.get('temp-inc', channel_num_ret_inc)
                parser.set(lineup_inc, channel_num_ret_inc, channel_nm_ret_inc)
                parser.remove_option('temp-inc', channel_num_ret_inc)
            parser.remove_section('temp-inc')
            sort_exc = sorted(parser.options(lineup_exc), key=natural_keys)
            parser.add_section('temp-exc')
            for s in sort_exc:
                channel_num_sort_exc = "%s" % s
                channel_nm_sort_exc = parser.get(lineup_exc, channel_num_sort_exc)
                parser.set('temp-exc', channel_num_sort_exc, channel_nm_sort_exc)
                parser.remove_option(lineup_exc, channel_num_sort_exc)
            ret_exc = parser.options('temp-exc')
            for s in ret_exc:
                channel_num_ret_exc = "%s" % s
                channel_nm_ret_exc = parser.get('temp-exc', channel_num_ret_exc)
                parser.set(lineup_exc, channel_num_ret_exc, channel_nm_ret_exc)
                parser.remove_option('temp-exc', channel_num_ret_exc)
            parser.remove_section('temp-exc')
        check_inc = len(parser.options(lineup_inc))
        if check_inc > 0:
            channel_id_inc = parser.items(lineup_inc)
            channel_number_inc = ( x[0] for x in channel_id_inc )
            channel_number_sub_inc = [re.sub("_\d\d\d\d\d", "", sub) for sub in channel_number_inc]
            channel_name_inc = ( x[1] for x in channel_id_inc )
            channels_inc = zip(channel_number_sub_inc, channel_name_inc)
            channel_list_inc = [ "%s - %s" % x for x in channels_inc ]
            channels_i = []
            for c in channel_list_inc:
                channels_i.append(c)
            sel_ch_inc = xbmcgui.Dialog().multiselect('Included Channels List - Click to Select Channels to Exclude', channels_i)
            if sel_ch_inc >= 0:
                add_num_inc = str(len(sel_ch_inc))
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Removing ' + add_num_inc + ' channels from the included lineup...', get_icon_path('minus'), 3000)
                channel_number_sel_inc = parser.options(lineup_inc)
                for s in sel_ch_inc:
                    channel_num_inc = channel_number_sel_inc[s]
                    channel_nm_inc = parser.get(lineup_inc, channel_num_inc)
                    parser.set(lineup_exc, channel_num_inc, channel_nm_inc)
                    parser.remove_option(lineup_inc, channel_num_inc)
            sort_inc = sorted(parser.options(lineup_inc), key=natural_keys)
            parser.add_section('temp-inc')
            for s in sort_inc:
                channel_num_sort_inc = "%s" % s
                channel_nm_sort_inc = parser.get(lineup_inc, channel_num_sort_inc)
                parser.set('temp-inc', channel_num_sort_inc, channel_nm_sort_inc)
                parser.remove_option(lineup_inc, channel_num_sort_inc)
            ret_inc = parser.options('temp-inc')
            for s in ret_inc:
                channel_num_ret_inc = "%s" % s
                channel_nm_ret_inc = parser.get('temp-inc', channel_num_ret_inc)
                parser.set(lineup_inc, channel_num_ret_inc, channel_nm_ret_inc)
                parser.remove_option('temp-inc', channel_num_ret_inc)
            parser.remove_section('temp-inc')
            sort_exc = sorted(parser.options(lineup_exc), key=natural_keys)
            parser.add_section('temp-exc')
            for s in sort_exc:
                channel_num_sort_exc = "%s" % s
                channel_nm_sort_exc = parser.get(lineup_exc, channel_num_sort_exc)
                parser.set('temp-exc', channel_num_sort_exc, channel_nm_sort_exc)
                parser.remove_option(lineup_exc, channel_num_sort_exc)
            ret_exc = parser.options('temp-exc')
            for s in ret_exc:
                channel_num_ret_exc = "%s" % s
                channel_nm_ret_exc = parser.get('temp-exc', channel_num_ret_exc)
                parser.set(lineup_exc, channel_num_ret_exc, channel_nm_ret_exc)
                parser.remove_option('temp-exc', channel_num_ret_exc)
            parser.remove_section('temp-exc')
        with open(xbmc.translatePath(u"special://userdata/addon_data/script.module.sd4tvh/filter.cfg"), 'w') as fp:
            fp.write("; sd4tvh channel filter\n")
            fp.write("; \n")
            fp.write("; Move channels to include under [<headend>-include].\n")
            fp.write("; Move channels to exclude under [<headend>-exclude].\n")
            fp.write("; Newly found channels appear under [<headend>-new].\n")
            fp.write("; Modify 'action = [include|exclude]' to specify how new channels should be handled.\n")
            fp.write("; Note: New channels are not automatically moved from the [<headend>-new] section.\n")
            fp.write("; Cut and paste newly found channels under [<headend>-include] or [<headend>-exclude].\n")
            fp.write("\n")
            parser.write(fp)
        xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'), 'Saving channels to ' + lineup_longname + '...', get_icon_path('tv'), 5000)



@plugin.route('/open_settings')
def open_settings():
    plugin.open_settings()


@plugin.route('/')
def index():
    items = []
    items.append(
    {
        'label': 'Configure Settings and Options',
        'path': plugin.url_for(u'open_settings'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': 'Add Schedules Direct Provider Lineup',
        'path': plugin.url_for(u'add_provider'),
        'thumbnail':get_icon_path('plus'),
    })
    items.append(
    {
        'label': 'Remove Schedules Direct Provider Lineup',
        'path': plugin.url_for(u'remove_provider'),
        'thumbnail':get_icon_path('minus'),
    })
    items.append(
    {
        'label': 'Add & Remove Channels from Lineup',
        'path': plugin.url_for(u'review_channels'),
        'thumbnail':get_icon_path('tv'),
    })

    return items


if __name__ == '__main__':
    plugin.run()
