#!/bin/sh

################################################################################
#      This file is part of OpenELEC - http://www.openelec.tv
#      Copyright (C) 2009-2014 Stephan Raue (stephan@openelec.tv)
#
#  OpenELEC is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 2 of the License, or
#  (at your option) any later version.
#
#  OpenELEC is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with OpenELEC.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

. /etc/profile

ADDON_HOME="$HOME/.kodi/userdata/addon_data/script.module.sd4tvh"
ADDON_DIR="$HOME/.kodi/addons/script.module.sd4tvh"
ADDON_SETTINGS="$ADDON_HOME/settings.xml"
if [ $# -lt 1 ]
then
  CD=`pwd`
  cd $ADDON_HOME
  USERID=`grep id=\"sd.username\" $ADDON_SETTINGS | awk '{print $3 }' | sed -e "s,value=,," -e "s,\",,g"`
  PASSWORD=`grep id=\"sd.password\" $ADDON_SETTINGS | awk '{print $3 }' | sed -e "s,value=,," -e "s,\",,g"`
  python $ADDON_DIR/sd4tvh.py -u $USERID -p $PASSWORD --channels --filter > sd4tvh.log 2>&1
  cd $CD
  exit 0
fi
exit 0
