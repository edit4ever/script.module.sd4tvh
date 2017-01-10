import time,datetime
import xbmc
import xbmcaddon

from datetime import date, timedelta

ADDON = xbmcaddon.Addon(id='script.module.sd4tvh')


class AutoUpdater:
    def update(self):
        hours_list = [6, 12, 24, 48]
        hours = hours_list[int(ADDON.getSetting('subscription_timer'))]
        xbmc.log('[Schedules Direct] Updating', level=xbmc.LOGNOTICE)
        xbmc.log('[Schedules Direct] Updating xmltv', level=xbmc.LOGNOTICE)
        xbmc.executebuiltin('RunPlugin(plugin://script.module.sd4tvh/import_schedule)')
        xbmc.executebuiltin('RunPlugin(plugin://script.module.sd4tvh/export_xmltv)')
        now = datetime.datetime.now()
        ADDON.setSetting('service_time', str(now + timedelta(hours=hours)).split('.')[0])
        xbmc.log("[Schedules Direct] updated. Next run at " + ADDON.getSetting('service_time'), level=xbmc.LOGNOTICE)


    def runProgram(self):
        if ADDON.getSetting('login_update') == "true":
            delay = int(ADDON.getSetting('login_delay'))
            time.sleep(delay*60)
            self.update()
        while not xbmc.abortRequested:
            if ADDON.getSetting('subscription_update') == "true":
                try:
                    next_run  = datetime.datetime.fromtimestamp(time.mktime(time.strptime(ADDON.getSetting('service_time').encode('utf-8', 'replace'), "%Y-%m-%d %H:%M:%S")))
                    now = datetime.datetime.now()
                    if now > next_run:
                        self.update()
                except Exception as detail:
                    xbmc.log("[Schedules Direct] Update Exception %s" % detail, level=xbmc.LOGERROR)
                    pass
            time.sleep(1)


xbmc.log("[Schedules Direct] service starting...", level=xbmc.LOGNOTICE)
AutoUpdater().runProgram()
