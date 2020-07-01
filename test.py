import requests
import bs4
from datetime import datetime, timedelta
from pprint import pprint as print
from PIL import Image
import requests
from io import BytesIO


date = datetime.now()
images = []
for i in range(0, 15):
    url = "https://sohowww.nascom.nasa.gov/data/synoptic/sunspots/sunspots_1024_{y}{m}{d}.jpg" \
        .format(y=date.year,
                m="{:02d}".format(date.month),
                d="{:02d}".format(date.day))
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    images.append(img)
    date -= timedelta(days=1)

images[0].save('spots.gif',
               save_all=True, append_images=images[1:], optimize=True, loop=1)

exit()

cam2url = {
            "c2": "https://sohowww.nascom.nasa.gov/data/LATEST/current_c2.gif",
            "c3": "https://sohowww.nascom.nasa.gov/data/LATEST/current_c3.gif",
            "eit171": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_171.gif",
            "eit195": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_195.gif",
            "eit284": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_284.gif",
            "eit304": "https://sohowww.nascom.nasa.gov/data/LATEST/current_eit_304.gif",
            "hmiigr": "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_igr-512.mpg",
            "hmimag": "https://sohowww.nascom.nasa.gov/data/LATEST/current_hmi_mag-512.mpg",
            "sunspots": ""
        }
url = cam2url["hmiigr"]
import ffmpy
ff = ffmpy.FFmpeg(
    inputs={url: None},
    outputs={'output.gif': None}
)
ff.run()
exit()
def get_images(date=None):
    # https://sohowww.nascom.nasa.gov/data/realtime/image-description.html
    date = date or datetime.now().replace(second=0, microsecond=0)
    spots = "https://sohowww.nascom.nasa.gov/data/synoptic/sunspots/sunspots_1024_{y}{m}{d}.jpg" \
                    .format(y=date.year,
                            m="{:02d}".format(date.month),
                            d="{:02d}".format(date.day))
    images = {
        "sunspots": [{"date": date.date(), "imgLink": spots}]
    }

    urls = [
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit171/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/c2/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/c3/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit171/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit195/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit284/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/eit304/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/hmiigr/{y}{m}{d}",
        "https://soho.nascom.nasa.gov/data/REPROCESSING/Completed/{y}/hmimag/{y}{m}{d}"
        ]

    for url in urls:
        url = url.format(y=date.year,
                         m="{:02d}".format(date.month),
                         d="{:02d}".format(date.day))
        img_type = url.split("/")[-2]
        images[img_type] = []
        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        for pic in soup.find_all("tr"):
            a = pic.find("a")
            if a:
                imgLink = url + "/" + a["href"]
                if not imgLink.endswith(".jpg") or not "1024" in imgLink:
                    continue
                # parse picture url for photo date
                hour = int(a["href"].split("_")[1][:2])
                minutes = int(a["href"].split("_")[1][2:])
                dt = date.replace(hour=hour, minute=minutes)
                images[img_type] += [{"date": dt, "imgLink": imgLink}]

    return images

print(get_images())

