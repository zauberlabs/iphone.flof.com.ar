#!/usr/bin/env python
#
# iphone.flof.com.ar provides a nice UI to access flof data from an iphone
#
# Copyright (c) 2008 by Zauber S.A. <www.zauber.com.ar>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from sys import path
path.append('site-packages')
import web, os, urllib2
from web import template
from BeautifulSoup import BeautifulStoneSoup
from datetime import datetime



urls = (
    '/',                                    'RootController',
    '/place/(\d+)',                         'RedirectArgumentController',
    '/place/(\d+)/',                        'PlaceController',
    '/recent/',                             'RecentController',
    '/recent/(\d+)',                        'RedirectArgumentController',
    '/recent/(\d+)/',                       'RecentController',
    '/label/([^+\\"><|/]+)/',                'LabelController',
    '/label/([^+\\"><|/]+)/(\d+)/',         'LabelController',
)


class RootController:
    def GET(self):
        print render.header()
        print render.root()
        print render.footer()

class RedirectArgumentController:
    def GET(self, argument):
        web.seeother(argument + '/')

class RecentController:
    def GET(self, page=1):
        prefix = '..'
        page = int(page)
        spots = flof.recent(page)
        if page == 1:
                print render.header(prefix)
                print render.spots(spots, prefix, 'Recent Places')
                print render.footer()
        elif len(spots):
                print render.recentpage(spots, page)

class LabelController:
    def GET(self, label, page=1):
        prefix = '../..'
        page = int(page)
        referer = web.ctx.env.get('HTTP_REFERER')
        if referer == None:
                referer = prefix
        spots =  flof.label(label, page)
        if page == 1:
                print render.header(referer)
                print render.spots(spots, prefix, 
                                  'Places labeled with `%s\'' % label)
                print render.footer()
        elif len(spots):
                print render.recentpage(flof.label(label, page), page, label)



class PlaceController:
    def GET(self, id):
        referer = web.ctx.env.get('HTTP_REFERER')
        if referer == None:
                referer = '../../'
        print render.header(referer)
        print render.place(flof.geoinfo(id))
        print render.footer()

class FlofFacade:
    headers = {}
    URL_BASE   = 'http://test.flof.com.ar'
    #URL_BASE  = 'http://localhost:9091'
    URL_SPOT   = '%s/feeds/xml/geoinfo/%s/'
    URL_RECENT = '%s/feeds/xml/recent/?page=%s'
    URL_LABEL  = '%s/feeds/xml/label/%s/?page=%s'
    URL_THUMB  = '%s/bin/spot/image/?action=thumb&imageid=%s'

    def label(self, label, page=1):
        return self._parseSpots(self._retrieve(
                self.URL_LABEL % (self.URL_BASE, label, page)), page)

    def recent(self, page=1):
        return self._parseSpots(self._retrieve(
                self.URL_RECENT % (self.URL_BASE, page)), page)
 
    def geoinfo(self, id):
        soup = self._retrieve(self.URL_SPOT % (self.URL_BASE, id))
        ret = { 'urls': [],
                'geocoding': [],
                'photos': [],
                'reviews': [],
                'name':  soup.geoinfo['name'],
                'lat':  soup.geoinfo['lat'],
                'lon':  soup.geoinfo['lon'],
              }
        for i in soup.findChildren('spot'):
            if i['geocoding']:
                ret['geocoding'].append(i['geocoding'])
            if i['url']:
                ret['urls'].append(i['url'])
            if i['photo_url']:
                ret['photos'].append({
                       'url':   i['photo_url'],
                       'thumb': self.URL_THUMB % (self.URL_BASE, i['id']),
                   })

            if i['description']:
                ret['reviews'].append({
                    'owner': i['owner'],
                    'text':  i['description'],
                    'date':  datetime.strptime(i.date.contents[0][:-9], 
                                              "%Y-%m-%d %H:%M:%S")
                })
        ret['urls'].sort()
        ret['geocoding'].sort()
        ret['photos'].sort()
        ret['reviews'].sort(lambda x, y: cmp(y['date'], x['date']))

        ret['urls'] = uniquer(ret['urls'])
        ret['geocoding'] = uniquer(ret['geocoding'])
        ret['photos'] = uniquer(ret['photos'], lambda x: x['url'])
        labels = {}
        for i in soup.findChildren('label'):
            label = i['name']
            if label in labels:
                labels[label] = labels[label] + 1
            else:
                labels[label] = 1
        ret['labels'] = labels
        return ret 

    def _retrieve(self, url):
        """ retrives a remote xml  """
        y = urllib2.urlopen(url)
        xml = y.read()
        y.close()
        return BeautifulStoneSoup(xml,  convertEntities='xml', smartQuotesTo='xml')
    def _parseSpots(self, soup, page):
        spots = []
        for i in soup.findChildren('spot'):
            spot = {
                'id':     i['id'],
                'name':   i.geoinfo['name'],
                'labels': [ j['name'] for j in i.findChildren('label') ],
            }
            spot['labels'].sort()
            spots.append(spot)
        return spots 

def uniquer(seq, idfun=None):
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result

    
#########################################################################

render = web.template.render('templates/', cache='DEV' not in os.environ)
template.Template.globals['len'] = len
template.Template.globals['version'] = '0.0'
flof = FlofFacade()

if __name__ == "__main__":

    if 'DEV' in os.environ:
        middleware = [web.reloader]
    else:
        middleware = []
    web.run(urls, globals(), *middleware)
