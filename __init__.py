from mycroft import intent_file_handler, intent_handler, MycroftSkill
from mycroft.skills.core import resting_screen_handler
from requests_cache import CachedSession
from datetime import timedelta, datetime
from mtranslate import translate
from lingua_franca.format import nice_date
from lingua_franca.parse import extract_datetime, extract_number
from mycroft.util import create_daemon
from adapt.intent import IntentBuilder
import bs4
import random
import tempfile
from os.path import join, exists
from PIL import Image
from io import BytesIO
import ffmpy


class HelioViewerSkill(MycroftSkill):

    def __init__(self):
        super(HelioViewerSkill, self).__init__(name="HelioViewerSkill")
        self.session = CachedSession(backend='memory',
                                     expire_after=timedelta(hours=6))
        self.translate_cache = {}  # save calls to avoid ip banning
        self.img_cache = {}  # dont re-parse for speed
        self.current_date = datetime.now()
        self.current_camera = "sunspots"
        create_daemon(self.bootstrap)

    def initialize(self):
        self.add_event('skill-helioviewer.jarbasskills.home',
                       self.handle_homescreen)

    # homescreen
    def handle_homescreen(self, message):
        self.gui.show_url("https://helioviewer.org/",  override_idle=True)

    # web apis
    def get_soho(self, date=None):
        # https://sohowww.nascom.nasa.gov/data/realtime/image-description.html
        date = date or datetime.now()
        date = date.replace(minute=0, second=0, microsecond=0)
        if date in self.img_cache:
            return self.img_cache[date]
        images = {}

        urls = [
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/c2/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/c3/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit171/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit195/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit284/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit304/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/hmiigr/{y}{m}{d}",
            "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/hmimag/{y}{m}{d}"
        ]
        cams = ["c2", "c3",
                "eit171", "eit195", "eit284", "eit304",
                "hmiigr", "hmimag"]
        for idx, url in enumerate(urls):
            # gui
            cam = cams[idx]
            caption = self.dialog_renderer.render(cam, {})
            if cam == "c2":
                title = "LASCO C2  -  "
            elif cam == "c3":
                title = "LASCO C3  -  "
            elif cam == "eit171":
                title = "EIT 171  -  "
            elif cam == "eit195":
                title = "EIT 195  -  "
            elif cam == "eit284":
                title = "EIT 284  -  "
            elif cam == "eit304":
                title = "EIT 304  -  "
            elif cam == "hmimag":
                title = "Michelson Doppler Imager Magnetogram  -  "
            else:  # if self.current_camera == "hmiigr":
                title = "Michelson Doppler Imager Continuum  -  "

            url = url.format(y=date.year,
                             m="{:02d}".format(date.month),
                             d="{:02d}".format(date.day))
            img_type = url.split("/")[-2]
            images[img_type] = []
            r = self.session.get(url)
            soup = bs4.BeautifulSoup(r.text, "html.parser")
            for pic in soup.find_all("tr"):
                a = pic.find("a")
                if a:
                    if not a["href"].endswith(".jpg") or \
                            not "1024" in a["href"]:
                        continue
                    # parse picture url for photo date
                    hour = int(a["href"].split("_")[1][:2])
                    minute = int(a["href"].split("_")[1][2:])
                    dt = date.replace(hour=hour, minute=minute,
                                      second=0, microsecond=0)
                    images[img_type] += [{"date_str": str(dt),
                                          "title": title + str(dt),
                                          "caption": caption,
                                          "imgLink": url + "/" + a["href"]}]
        self.img_cache[date] = images
        return images

    def get_silso(self):
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
                            day=int(line[8:10].strip()))
            date = date.date()
            picture_url = "https://sohowww.nascom.nasa.gov/data/synoptic/sunspots/sunspots_1024_{y}{m}{d}.jpg" \
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
                    if pcchange >= 2:
                        increase = True
                change = n - prev

            # title + caption
            title = "Sunspots - " + str(date)
            caption = str(n) + " sunspots"
            if increase:
                caption += "\nA significant increase with " + \
                           str(change) + " new spots"
            elif decrease:
                caption += "\nA significant decrease with " + \
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
        data = self.get_silso()
        images = self.get_soho(date)

        if date is not None:
            for d in data:
                if d["date_str"] == str(date.date()):
                    data = d
                    break
            else:
                data = data[-1]
                # TODO error dialog
        else:
            data = data[-1]
        data["images"] = images

        if self.current_camera != "sunspots":
            data["imgLink"] = images[self.current_camera][-1]["imgLink"]
            data["title"] = images[self.current_camera][-1]["title"]
            data["caption"] = images[self.current_camera][-1]["caption"]

        tx = ["title", "caption"]

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
        self.current_date = date or datetime.strptime(data["date_str"],
                                                      "%Y-%m-%d")

        for k in data:
            self.gui[k] = data[k]
        self.set_context("SunSpots", self.current_camera)
        return data

    @resting_screen_handler("SOHO")
    def idle(self, message):
        cam2url = {
            "c2": "https://sohowww.nascom.nasa.gov/data/LATEST/current_c2.gif",
            "c3": "https://sohowww.nascom.nasa.gov/data/LATEST/current_c3.gif",
            "eit171": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_171.gif",
            "eit195": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_195.gif",
            "eit284": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_284.gif",
            "eit304": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_304.gif",
            "hmiigr": self.vid2gif(
                "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_igr-512.mpg"),
            "hmimag": self.vid2gif(
                "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_mag-512.mpg"),
            "sunspots": self._sunspot_gif()
        }
        # TODO self.settings checkbox for cameras
        cams = ["c2", "c3",
                "eit171", "eit195", "eit284", "eit304",
                "hmiigr", "hmimag"]
        cam = message.data.get("cam") or random.choice(cams)
        self.current_camera = cam
        picture = cam2url[self.current_camera]
        self.gui.show_animated_image(picture, override_idle=True,
                                     fill='PreserveAspectFit')

    # intents
    def _display(self, date):
        data = self.update_picture(date)
        url = data["imgLink"]
        title = data["title"]
        caption = data["caption"]

        if self.current_camera == "sunspots":
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
        else:
            self.speak(caption)
        self.gui.show_image(url, override_idle=60,
                            title=title,
                            fill='PreserveAspectFit', caption=caption)

    @intent_file_handler("helioviewer.intent")
    def handle_helioviewer_intent(self, message):
        self.handle_homescreen(message)

    @intent_file_handler("number.intent")
    @intent_file_handler("number_date.intent")
    def handle_spot_count_intent(self, message):
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        self.current_camera = "sunspots"
        self._display(date)

    @intent_handler(IntentBuilder("MDIIntent").require("sun")
                    .optionally("visible").require("picture"))
    @intent_handler(IntentBuilder("MDIIntent2").require("mdi")
                    .optionally("sun").optionally("visible")
                    .optionally("picture"))
    def handle_mdi(self, message):
        self.current_camera = "hmiigr"
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        self._display(date)
        self.set_context("MDI" + self.current_camera)

    @intent_handler(IntentBuilder("MagnetosphereIntent").require("sun")
                    .require("magnetic").optionally("picture"))
    def handle_mag(self, message):
        self.current_camera = "hmimag"
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        self._display(date)
        self.set_context("MDI" + self.current_camera)

    @intent_handler(IntentBuilder("LASCOIntent").require("lasco")
                    .optionally("inner").optionally("outer")
                    .optionally("picture"))
    def handle_lasco(self, message):
        if message.data.get("inner"):
            self.current_camera = "c2"
        elif message.data.get("outer"):
            self.current_camera = "c3"
        else:
            self.current_camera = random.choice(["c2", "c3"])
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        self._display(date)
        self.set_context("LASCO" + self.current_camera)

    @intent_handler(IntentBuilder("EITIntent").require("eit").require("sun")
                    .optionally("high").optionally("low")
                    .optionally("atmosphere").optionally("temperature")
                    .optionally("picture"))
    def handle_eit(self, message):
        camera = random.choice(["eit304", "eit171", "eit195", "eit284"])
        n = extract_number(message.data["utterance"], ordinals=True)
        if n is not False:
            if n in [284, 304, 195, 171]:
                camera = "eit" + str(n)
            elif message.data.get("temperature"):
                if n >= 2000000:
                    camera = "eit284"
                elif n >= 1500000:
                    camera = "eit195"
                elif n >= 1000000:
                    camera = "eit171"
                else:
                    camera = "eit304"
        # the hotter the temperature,
        # the higher you look in the solar atmosphere.
        elif message.data.get("high"):
            camera = "eit284"  # 2 million degrees
        elif message.data.get("low"):
            #  304 Angstrom the bright material is at 60,000 to 80,000 degrees Kelvin.
            camera = "eit304"
        self.current_camera = camera
        date = extract_datetime(message.data["utterance"], lang=self.lang)
        if date is not None:
            date, remainder = date
        self._display(date)
        self.set_context("EIT" + self.current_camera[3:])

    @intent_handler(IntentBuilder("PrevSunPictureIntent")
                    .require("previous").require("picture")
                    .require("SunSpots"))
    def handle_prev(self, message):
        date = self.current_date - timedelta(days=1)
        self._display(date)

    @intent_handler(IntentBuilder("NextSunPictureIntent")
                    .require("next").require("picture").require("SunSpots"))
    def handle_next(self, message):
        date = self.current_date + timedelta(days=1)
        self._display(date)

    @intent_handler(IntentBuilder("AnimateSunPictureIntent")
                    .require("animate").optionally("picture").require("SunSpots"))
    def handle_animate(self, message):
        self.speak_dialog("animation")
        message.data["cam"] = self.current_camera
        self.idle(message)

    # utils
    def bootstrap(self):
        # speed up on load - cache
        self.vid2gif(
            "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_igr-512.mpg")
        self.vid2gif(
            "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_mag-512.mpg")
        self._sunspot_gif()

    def vid2gif(self, url):
        # once a day only
        name = url.split("/")[-1].replace(".mpg", ".gif")
        path = join(tempfile.gettempdir(), str(datetime.now().date()) + name)
        if not exists(path):
            ff = ffmpy.FFmpeg(
                inputs={url: None},
                outputs={path: None}
            )
            ff.run()
        return path

    def _sunspot_gif(self, n_days=30):
        urls = []
        date = datetime.now()
        for i in range(n_days):
            url = "https://sohowww.nascom.nasa.gov/data/synoptic/sunspots/sunspots_1024_{y}{m}{d}.jpg" \
                .format(y=date.year,
                        m="{:02d}".format(date.month),
                        d="{:02d}".format(date.day))
            date -= timedelta(days=1)
            urls.append(url)
        urls.reverse()

        # once a day only
        path = join(tempfile.gettempdir(), str(date.date()) + ".gif")
        if not exists(path):
            images = []
            for url in urls:
                response = self.session.get(url)
                img = Image.open(BytesIO(response.content))
                images.append(img)
            images[0].save(path,
                           save_all=True, append_images=images[1:],
                           optimize=True, loop=0)
        return path


def create_skill():
    return HelioViewerSkill()
