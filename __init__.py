
from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

import requests

__author__ = 'rboatright'

LOGGER = getLogger(__name__)


class SunspotSkill(MycroftSkill):

    def __init__(self):
        super(SunspotSkill, self).__init__(name="SunspotSkill")

    def initialize(self):
        spot_count_intent = IntentBuilder("SpotCountIntent").\
            require("SunspotKeyword").build()
        self.register_intent(spot_count_intent, self.handle_spot_count_intent)
                

    def handle_spot_count_intent(self, message):
    	spdata = requests.get("http://www.sidc.be/silso/DATA/EISN/EISN_current.csv")
    	sptext = spdata.text
    	splines = sptext.splitlines()
    	splines.reverse()
    	spfields = splines[1].split(',')
    	data = {'spotcount': spfields[4], 'stations': spfields[7]}
    	self.speak_dialog("sunspots", data)
    	        
    def stop(self):
        pass


def create_skill():
    return SunspotSkill()
