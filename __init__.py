
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
    	spyfields = splines[2].split(',')
    	chngcomment = " "
    	pcchange = float(spyfields[4]) / float(spfields[4]) 
    	if ( pcchange < 0.5 ) :
    		chngcomment = " down a lot "
    		
    	if ( pcchange > 2 ) :
    		chngcomment = " up a lot "
    	    	   	
    	data = {'spotcount': spfields[4], 'stations': spfields[7], 'spcomment': chngcomment}
    	if ( int(spfields[4]) == 0 ) :
    		words = "Wow, it's blank. No spots at all."
    		self.speak(words)
    	else:
    		self.speak_dialog("sunspots", data)
    	        
    def stop(self):
        pass


def create_skill():
    return SunspotSkill()
