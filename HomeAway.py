from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import html
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import time
import json
import csv
import math
import argparse

def get_days_between_today(d2):
    d1 = datetime.strptime(datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return (abs(d2 - d1).days)

def get_long_lat(radius, lat, long):
    #convert to km
    radius = radius * 1.60934

    u_lat = lat  + (radius / 6378) * (180 / math.pi)
    u_long = long + (radius / 6378) * (180 / math.pi) / math.cos(lat * math.pi/180)

    b_lat = lat  - (radius / 6378) * (180 / math.pi)
    b_long = long - (radius / 6378) * (180 / math.pi) / math.cos(lat * math.pi/180)
    return u_lat, u_long, b_lat, b_long

def write_csv(propertyPrices, listHeader):
    with open("properties.csv" , 'w') as outcsv:
        writer = csv.writer(outcsv, delimiter =',')
        writer.writerow(g for g in listHeader)
        for row in propertyPrices:
            writer.writerow(row)

def get_url(address, u_lat, u_long, b_lat, b_long):
    addressF = address.replace(" ","-").replace(",","")
    radiusF = str(b_lat) + "," + str(b_long) + "," + str(u_lat) + "," + str(u_long)
    return addressF, radiusF

def set_driver():
    CHROMEDRIVER_PATH = '/bin/chromedriver'
    WINDOW_SIZE = "1920,1080"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def append_daterange(list):
    dates = []
    for i in range(365):
         date = str(datetime.strptime(datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d")+timedelta(days=i)).split(" ")[0]
         dates.append(date)
         list.append(date)
    return list, dates

def topThreeProperties(daysBetween, rentPriceList):
    topThree = []
    topThreeIndex = []
    max = []
    maxPrice = 0
    maxIndex = 0
    for j in range(3):
        for i in range(daysBetween,daysBetween+365):
            if int(rentPriceList[i])>maxPrice and i not in topThreeIndex:
                maxPrice = int(rentPriceList[i])
                maxIndex = i-daysBetween+2
                max = [maxPrice,maxIndex]
        topThree.append(max)
        topThreeIndex.append(maxIndex+daysBetween-2)
        maxPrice = 0
    topThree.sort(reverse=True)
    return topThree

def get_json_output(address,radius):
    radius = int(radius)
    propertyJSON = homeaway_parse(address, radius, True)
    return propertyJSON

def homeaway_parse(address, radius, api):
    driver = set_driver()

    geolocator = Nominatim(user_agent="HomeAway")
    location = geolocator.geocode(address)
    u_lat, u_long, b_lat, b_long = get_long_lat(radius,location.latitude,location.longitude)
    addressF, radiusF = get_url(address, u_lat, u_long, b_lat, b_long)
    #mainurl = "https://www.homeaway.com/search/keywords:michigan-and-wacker-chicago-il/arrival:2019-07-14/departure:2019-07-18?adultsCount=2&petIncluded=false"
    mainurl = "https://www.homeaway.com/search/keywords:" + addressF + "/@" + radiusF + "15z?petIncluded=false&ssr=true"

    driver.get(mainurl)
    time.sleep(2)
    response = driver.page_source
    driver.close()

    parser = html.fromstring(response)

    search_results = parser.xpath('//div[@class="HitCollection"]')
    for names in search_results:
        links = names.xpath('.//h4[@class="HitInfo__headline hover-text"]/@href')

    listHeader = ["PropertyName", "Website"]
    listHeader, dates = append_daterange(listHeader)
    listHeader.append("maxDate1")
    listHeader.append("maxDate2")
    listHeader.append("maxDate3")

    propertyJSON= []
    propertyPrices =[]
    print("parsing")
    for num, l in enumerate(links):
        url = "https://www.homeaway.com" + l
        print (num, url)
        driver = set_driver()
        driver.get(url)
        time.sleep(2)
        response = driver.page_source
        driver.close()

        parser = html.fromstring(response)
        jsonStr = parser.xpath('//body//script/text()')[0]
        jsonStr = jsonStr.split("};")[0]+"}"
        jsonStr = jsonStr.replace("window.__INITIAL_STATE__ = ","").replace("window.__REQUEST_STATE__ = ","")

        data = json.loads(jsonStr)
        propertyName = data['listingReducer']['headline']
        beginDate = data['listingReducer']['rateSummary']['beginDate']
        endDate = data['listingReducer']['rateSummary']['endDate']
        latitude = data['listingReducer']['geoCode']['latitude']
        longitude = data['listingReducer']['geoCode']['longitude']
        rentPrices = data['listingReducer']['rateSummary']['rentNightsConverted'].replace("'","")
        rentPriceList = rentPrices.split(",")
        daysBetween = int(get_days_between_today(beginDate))
        properties = [propertyName, url]

        for i in range(daysBetween,daysBetween+365):
            properties.append(rentPriceList[i])

        propertyPrices.append(properties)
        topThree = topThreeProperties(daysBetween, rentPriceList)
        date1 = topThree[0][1]
        date2 = topThree[1][1]
        date3 = topThree[2][1]
        propertyPrices[num].append(str(listHeader[date1]))
        propertyPrices[num].append(str(listHeader[date2]))
        propertyPrices[num].append(str(listHeader[date3]))
        maxDates = [str(listHeader[date1]), str(listHeader[date2]), str(listHeader[date3])]

        propertyJSON.append({"propertyName":propertyName,
                              "website":url,
                              "Dates": dates,
                              "rates": properties[2:-3],
                              "maxDates": maxDates
                              })

    print("parsing complete,", num+1)
    if not api:
        print ("writing csv")
        write_csv(propertyPrices, listHeader)

    return propertyJSON

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("address", type = str, help = "the address")
    parser.add_argument("radius", type = int, help = "radius in miles")
    args = parser.parse_args()
    address = args.address
    radius = args.radius
    propertyJSON = homeaway_parse(address, radius, False)
    print ("csv complete")
