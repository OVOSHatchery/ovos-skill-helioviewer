from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

import requests
import arrow

__author__ = 'rboatright'

LOGGER = getLogger(__name__)

class sunspots(MycroftSkill):
    def __init__(self):
        super(sunspots, self).__init__(name="sunspots")

    def initialize(self):
        self.load_data_files(dirname(__file__))
        sunspots_intent = IntentBuilder("sunspotsIntent").\
            require("sunspots").build()
        self.register_intent(sunspots_intent, self.handle_sunspots_intent)

    def handle_sunspots_intent(self, message):
        r = requests.get("http://www.solarham.net/summary.txt")
        t = str(r.json()['launches'][0]['windowstart'])
        try:
                self.speak_dialog("space.launch", data={'sunspots': r})

                                                    
        except:
            self.speak_dialog("not.found")
        
    def stop(self):
        pass


def create_skill():
    return sunspots()
