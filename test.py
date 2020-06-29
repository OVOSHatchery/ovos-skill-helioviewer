from datetime import datetime
import requests


def current():
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
    txt = requests.get(url).text
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
            prev = int(lines[idx-1][20:23].strip())
            if prev != n:
                pcchange = float(n / (prev + 0.000000001))
                if pcchange < 0.5:
                    decrease = True
                if pcchange >= 1:
                    increase = True
            change = n - prev

        data = {
            "date_str": str(date),
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

current()
print(15/10)