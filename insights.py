import time
import json
import db
import os
import datetime 
from enum import Enum

class lightNeeded(Enum):

    NEED_MORE = "More light needed"

    SATISFIED = "Light requirement satisfied"

    NEED_LESS = "Less light needed"

deviceId = os.environ.get("DEVICE_ID")

recommendedLuxValues = [
    "Diffuse light ( Less than 5,300 lux / 500 fc)",
    "Strong light ( 21,500 to 3,200 lux/2000 to 300 fc)",
    "Full sun (+21,500 lux /+2000 fc )",
];

def moistureReasoning(sensorValue, apiValue):

    recommendedValues = [
        "Keep moist between watering & Can dry between watering",
        "Water when soil is half dry & Can dry between watering",
        "Water when soil is half dry & Change water regularly in the cup",
        "Keep moist between watering & Water when soil is half dry",
        "Keep moist between watering & Must not dry between watering",
        "Must dry between watering & Water only when dry",
        "Change water regularly in the cup & Water when soil is half dry"
    ];

    plantMoistureReport = {
        "Soil status": "",
        "Watering required": "",
	"Last watered": ""
    }

    if sensorValue < 400:
        plantMoistureReport["Soil status"] = "Very dry"

    if (399 < sensorValue) & (sensorValue < 500):
        plantMoistureReport["Soil status"] = "Dry"

    if (499 < sensorValue) & (sensorValue < 600):
        plantMoistureReport["Soil status"] = "Half dry"

    if (599 < sensorValue) & (sensorValue < 700):
        plantMoistureReport["Soil status"] = "Moist"

    if (699 < sensorValue) & (sensorValue < 800):
        plantMoistureReport["Soil status"] = "Wet"

    if 799 < sensorValue:
        plantMoistureReport["Soil status"] = "Just watered"

    if (apiValue == recommendedValues[0]) | (apiValue == recommendedValues[3]) | (apiValue == recommendedValues[4]):
        if sensorValue < 600:
            plantMoistureReport["Watering required"] = "Yes <i class='bi bi-exclamation-triangle'></i>"
        else:
            plantMoistureReport["Watering required"] = "No"

    if (apiValue == recommendedValues[1]) | (apiValue == recommendedValues[2]) | (apiValue == recommendedValues[6]):
        if sensorValue < 500:
            plantMoistureReport["Watering required"] = "Yes <i class='bi bi-exclamation-triangle'></i>"
        else:
            plantMoistureReport["Watering required"] = "No"

    if apiValue == recommendedValues[5]:
        if sensorValue < 400:
            plantMoistureReport["Watering required"] = "Yes <i class='bi bi-exclamation-triangle'></i>"
        else:
            plantMoistureReport["Watering required"] = "No"

    plantMoistureReport["Last watered"] = datetime.datetime.strftime(db.get_last_watered(deviceId), "%Y-%m-%d %H:%M:%S")

    return plantMoistureReport


def luxReasoning(sensorValue, apiValue):
    
    luxValues = db.get_lux(deviceId)
    
    secondsToday = lux_today(luxValues, apiValue, datetime.date.today())
    secondsWeek = lux_today(luxValues, apiValue, datetime.date.today() - datetime.timedelta(days=7))
    seconds30 = lux_today(luxValues, apiValue, datetime.date.today() - datetime.timedelta(days=30))

    lightToday = checkLightHours(secondsToday, apiValue)
    lightWeek = checkLightHours(secondsWeek / 7, apiValue)
    light30 = checkLightHours(seconds30 / 30, apiValue)

    plantLightReport = {
        "Position status": "",
        "Light exposure": "",
        "Daily report": lightToday,
        "Weekly report": lightWeek,
        "Monthly report": light30
    }

    if sensorValue < 5300:
        plantLightReport["Position status"] = "Diffuse light"

    if (5299 < sensorValue) & (sensorValue < 21500):
        plantLightReport["Position status"] = "Strong light"

    if 21499 < sensorValue:
        plantLightReport["Position status"] = "Full sun"

    if apiValue == recommendedLuxValues[0]:
        if sensorValue < 5300:
            plantLightReport["Light exposure"] = "Satisfied"
        else:
            plantLightReport["Light exposure"] = "Less light needed <i class='bi bi-exclamation-triangle'></i>"

    if apiValue == recommendedLuxValues[1]:
        if (5299 < sensorValue) & (sensorValue < 21500):
            plantLightReport["Light exposure"] = "Satisfied"
        elif sensorValue < 5230:
            plantLightReport["Light exposure"] = "More light needed <i class='bi bi-exclamation-triangle'></i>"
        elif 21499 < sensorValue:
            plantLightReport["Light exposure"] = "Less light needed <i class='bi bi-exclamation-triangle'></i>"

    if apiValue == recommendedLuxValues[2]:
        if 21499 < sensorValue:
            plantLightReport["Light exposure"] = "Satisfied"
        else:
            plantLightReport["Light exposure"] = "More light needed <i class='bi bi-exclamation-triangle'></i>"
    return plantLightReport

def lux_today(luxValues, apiValue, date):
  lux_dates = list(map(lambda lux: {"date": lux["date"], "lux": lux["lux"] }, luxValues))

  times = []

  total_time = 0

  for lux_date in lux_dates:
    if lux_date["date"].date() >= date:
      times.append({"time": lux_date["date"],"lux": lux_date["lux"]})

  i = 1
  
  while i < len(times):
    if (getRecommendation(float(times[i]["lux"]), apiValue) == 1) & (getRecommendation(float(times[i -1]["lux"]), apiValue) == 1):
      delta = (times[i]["time"] - times[i-1]["time"]).total_seconds()      
      total_time += delta
    i += 1
  print("total time:", total_time)
  return total_time

def checkLightHours (total_seconds, apiValue):
  total_hours = total_seconds/3600
  full_shade = 10800/3600
  full_sun = 21600/3600
  if apiValue == recommendedLuxValues[0]:
    if total_hours < full_shade:
        return {"Status": lightNeeded.SATISFIED.value, "Light per day": str(total_hours) + "h"}
    else:
        return {"Status": lightNeeded.NEED_LESS.value, "Light per day": str(total_hours) + "h", "Time from target": str(total_hours-full_shade) + "h"}
  elif apiValue == recommendedLuxValues[1]:
    if total_hours < full_shade:
        return {"Status": lightNeeded.NEED_MORE.value, "Light per day": str(total_hours) + "h", "Time from target": str(full_shade-total_hours) + "h"}
    elif total_hours > full_sun:
        return {"Status": lightNeeded.NEED_LESS.value, "Light per day": str(total_hours) + "h", "Time from target": str(total_hours-full_sun) + "h"}
    else:
        return {"Status": lightNeeded.SATISFIED.value, "Light per day": str(total_hours) + "h"}
  elif apiValue == recommendedLuxValues[2]:
    if total_hours > full_sun:
        return {"Status": lightNeeded.SATISFIED.value, "Light per day": str(total_hours) + "h"}
    else:
        return {"Status": lightNeeded.NEED_MORE.value, "Light per day": str(total_hours) + "h", "Time from target": str(full_sun-total_hours) + "h"}


def getRecommendation(sensorValue, apiValue):
    # 0 => more light needed
    # 1 => satisfied
    # 2 => less light needed

  if apiValue == recommendedLuxValues[0]:
    if sensorValue < 5300:
      return 1
    else:
      return 2
  if apiValue == recommendedLuxValues[1]:
    if (5299 < sensorValue) & (sensorValue < 21500):
      return 1
    elif sensorValue < 5230:
      return 0
    elif 21499 < sensorValue:
      return 2
  if apiValue == recommendedLuxValues[2]:
    if 21499 < sensorValue:
      return 1
    else:
      return 0
  raise ValueError("Error: Invalid api value.")

