from mycroft import intent_file_handler, intent_handler, MycroftSkill
from mycroft.skills.core import resting_screen_handler
from requests_cache import CachedSession
from datetime import timedelta, datetime
from mtranslate import translate
from lingua_franca.format import nice_date
from lingua_franca.parse import extract_datetime
from mycroft.util import create_daemon


class SunspotSkill(MycroftSkill):

    def __init__(self):
        super(SunspotSkill, self).__init__(name="SunspotSkill")
        self.session = CachedSession(backend='memory',
                                     expire_after=timedelta(hours=6))
        self.translate_cache = {}
        create_daemon(self.get_count)  # bootstrap cache

    def get_count(self):
        url = "http://www.sidc.be/silso/DATA/EISN/EISN_current.txt"
        # Line format [character position]:
        #  - [1-4]   Year
        #  - [6-8]   Month
        #  - [9-10]   Day
        #  - [12-19] Decimal date
        #  - [21-23] Estimated Sunspot Number
        #  - [25-29] Estimated Standard Deviation
        #  - [31-33] Number of Stations calculated
        #  - [35-37] Number of Stations available
        txt = self.session.get(url).text
        data_points = []
        lines = txt.split("\n")
        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            date = datetime(year=int(line[:4].strip()),
                            month=int(line[5:8].strip()),
                            day=int(line[8:10].strip())).date()
            picture_url = "https://sohowww.nascom.nasa.gov/data/synoptic/sunspots_earth/sunspots_1024_{y}{m}{d}.jpg" \
                .format(y=date.year,
                        m="{:02d}".format(date.month),
                        d="{:02d}".format(date.day))

            n = int(line[20:23].strip())
            decrease = False
            increase = False
            change = 0
            if idx > 0:
                prev = int(lines[idx - 1][20:23].strip())
                if prev != n:
                    pcchange = float(n / (prev + 0.000000001))
                    if pcchange < 0.5:
                        decrease = True
                    if pcchange >= 1:
                        increase = True
                change = n - prev

            # title + caption
            title = "Sunspots - " + str(date)
            caption = str(n) + " sunspots"
            if increase:
                caption = "\n It is a significant increase with " + \
                          str(n) + " new spots"
            elif decrease:
                caption = "\n It is a significant decrease with " + \
                          str(abs(change)) + " less spots"

            data = {
                "date_str": str(date),
                "human_date": nice_date(date, lang=self.lang),
                "title": title,
                "caption": caption,
                "imgLink": picture_url,
                "count": n,
                "standard_deviation": float(line[24:29].strip()),
                "n_stations": int(line[30:33].strip()),
                "total_stations": int(line[34:37].strip()),
                "increase": increase,
                "decrease": decrease,
                "change": change
            }
            data_points.append(data)
        return data_points

    # idle screen
    def update_picture(self, date=None):
        data = self.get_count()
        self.settings["raw"] = data
        dt1 = data[0]["date_str"]
        dt2 = data[-1]["date_str"]
        n = sum([n["count"] for n in data])
        title = "Recent Sunspots: " + dt1 + " - " + dt2
        caption = "There were " + str(n) + " sunspots in the past week"
        weekly = {"count": n,
                  "title": title,
                  "caption": caption,
                  "date-range": dt1 + " - " + dt2,
                  "days": data,
                  "images": [i["imgLink"] for i in data],
                  "imgLink": data[0]["imgLink"]}

        if date is not None:
            if isinstance(date, datetime):
                date = date.date()
            for d in data:
                if d["date_str"] == str(date):
                    data = d
                    break
            else:
                data = data[-1]
                # TODO error dialog
        else:
            data = data[-1]
        data["weekly"] = weekly
        tx = ["title", "caption", "weekly"]

        def tx_keys(bucket):
            for k in bucket:
                try:
                    if not self.lang.startswith("en") and k in tx:
                        if isinstance(bucket[k], dict):
                            bucket[k] = tx_keys(bucket[k])
                        elif isinstance(bucket[k], list):
                            for idx, d in enumerate(bucket[k]):
                                bucket[k][idx] = tx_keys(d)
                        elif bucket[k] not in self.translate_cache:
                            translated = translate(bucket[k], self.lang)
                            self.translate_cache[bucket[k]] = translated
                            bucket[k] = translated
                        else:
                            bucket[k] = self.translate_cache[bucket[k]]
                except:
                    continue  # rate limit from google translate
            return bucket

        data = tx_keys(dict(data))
        for k in data:
            if k != "weekly":
                self.settings[k] = data[k]
                self.gui[k] = data[k]
        self.set_context("SunSpots")
        return data

    @resting_screen_handler("SunSpots")
    def idle(self, message):
        self.update_picture()
        self.gui.clear()
        self.gui.show_page('idle.qml')

    @intent_file_handler("number.intent")
    @intent_file_handler("number_date.intent")
    def handle_spot_count_intent(self, message):
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        data = self.update_picture(date)
        self.gui.show_image(data["imgLink"], override_idle=True,
                            title=data["title"],
                            fill='PreserveAspectFit', caption=data["caption"])
        if data["count"] == 0:
            self.speak_dialog("nospots")
        elif date is not None:
            self.speak_dialog("sunspots.past",
                              {'spotcount': data["count"],
                               "date": data["human_date"],
                               'stations': data["n_stations"],
                               'spcomment': data["caption"]})
        else:
            self.speak_dialog("sunspots",
                              {'spotcount': data["count"],
                               'stations': data["n_stations"],
                               'spcomment': data["caption"]})

    @intent_file_handler("recent.intent")
    def handle_recent_spot_count_intent(self, message):
        data = self.update_picture()["weekly"]
        # TODO pages for each date
        self.gui.show_image(data["imgLink"], override_idle=True,
                            title=data["title"],
                            fill='PreserveAspectFit',
                            caption=data["caption"])
        if data["count"] == 0:
            self.speak_dialog("nospots")
        else:
            self.speak_dialog("recent",
                              {'spotcount': data["count"]})


def create_skill():
    return SunspotSkill()
