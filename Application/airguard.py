import time
import signal
import random
import uvicorn
import requests
import json
import warnings

from fastapi import FastAPI
from co_forecasting import load_model, pred
from send_emails import send_email
from calculate_aqi import calculate_aqi, turnicate_value
from datetime import datetime, timedelta

app = FastAPI()
running = True
PM10_ID = os.environ.get("PM10_ID")
mod_pm10 = os.environ.get("mod_pm10")
PM25_ID = os.environ.get("PM25_ID")
mod_pm25 = os.environ.get("mod_pm25")
OZONE_ID = os.environ.get("OZONE_ID")
mod_ozone = os.environ.get("mod_ozone")
CO_ID = os.environ.get("CO_ID")
mod_co = os.environ.get("mod_co")
NO2_ID = os.environ.get("NO2_ID")
mod_no2 = os.environ.get("mod_no2")
SO2_ID = os.environ.get("SO2_ID")
mod_so2 = os.environ.get("mod_so2")
url_put = os.environ.get("URL_PUT")
model_path = os.environ.get("MODEL_PATH")
receiver = os.environ.get("email_receiver")
ozone_breakpoints = [3, 8, 12, 15, 18, 20, 23, 25]
ozone_breakpoints_low = [0, 3.1, 8.1, 12.1, 15.1, 18.2, 20.1, 23.1]
pm25_breakpoints = [12.0, 35.4, 55.4, 150.4, 250.4, 350.4, 500.4]
pm25_breakpoints_low = [0, 12.1, 35.5, 55.5, 150.5, 250.5, 350.5]
pm10_breakpoints = [54, 154, 254, 354, 424, 504, 604]
pm10_breakpoints_low = [0, 55, 155, 255, 355, 425, 505]
co_breakpoints = [4.4, 9.4, 12.4, 15.4, 30.4, 40.4, 50.4]
co_breakpoints_low = [0.0, 4.5, 9.5, 12.5, 15.5, 30.5, 40.5]
so2_breakpoints = [35, 75, 185, 304, 604, 804, 1004]
so2_breakpoints_low = [0, 36, 76, 186, 305, 605, 804]
no2_breakpoints = [53, 100, 360, 649, 1249, 1649, 2049]
no2_breakpoints_low = [0, 54, 101, 361, 650, 1250, 1650]
AQI_values = [50, 100, 150, 200, 300, 400, 500]
so2_molecular_weight = 64.07
o3_molecular_weight = 48.0
no2_molecular_weight = 46.01
co_molecular_weight = 28.01
who_guideline = 10  # WHO annual air quality guideline for PM2.5 (µg/m³)


# Settings the warnings to be ignored
warnings.filterwarnings('ignore')

def updatenotes(aqi,id,token):
    payload = json.dumps([
        {
            "ref": {
                "id": id,
                "name": "notes"
            },
            "value": aqi
        },

    ])

    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json'
    }

    requests.request("PUT", url_put, headers=headers, data=payload, verify=False)

def ppb_to_ugm3(ppb, molecular_weight):
    concentration_ugm3 = (molecular_weight * ppb) / 24.45
    return concentration_ugm3

def ugm3_to_ppb(ugm3, molecular_weight):
    concentration_ppb = (24.45 * ugm3) / molecular_weight
    return concentration_ppb

def ppm_to_ugm3(ppm, molecular_weight):
    concentration_ugm3 = (molecular_weight * ppm) / 24.45
    return concentration_ugm3

def ugm3_to_ppm(ugm3, molecular_weight):
    concentration_ppm = (24.45 * ugm3) / molecular_weight
    return concentration_ppm

def find_aqi_category(number):
    if number >= 0 and number <= 50:
        category = "Good"
    elif number >= 51 and number <= 100:
        category = "Moderate"
    elif number >= 101 and number <= 150:
        category = "Unhealthy for Sensitive Groups"
    elif number >= 151 and number <= 200:
        category = "Unhealthy"
    elif number >= 201 and number <= 300:
        category = "Very unhealthy"
    elif number >= 301:
        category = "Hazardous"
    else:
        category = "Category not found"

    return category


def text_to_datetime(text_date):
    date_time_obj = datetime.strptime(text_date, "%Y-%m-%d %H:%M:%S")
    return date_time_obj


def get_token():
    # get token
    url = "https://localhost/auth/realms/master/protocol/openid-connect/token"

    payload = 'grant_type=client_credentials&client_id=mqttuser&client_secret=cAvOPNFUSaqddFo6JUrfYzkmyPEBFrTa&refresh_expires_in=40000'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    json_data = response.json()
    token = json_data["access_token"]

    return token

def get_concentrations(data):
    co_value = data['attributes']['co']['value']
    co_3hb_value = data['attributes']['co_j']['value']['co_3hb']
    co_2hb_value = data['attributes']['co_j']['value']['co_2hb']
    co_1hb_value = data['attributes']['co_j']['value']['co_1hb']

    return co_value, co_3hb_value, co_2hb_value, co_1hb_value


def get_value(data,attribute):

    att_value = data['attributes'][attribute]['value']

    return att_value

def create_payload(co_2hb_value, co_1hb_value, co_value, concentration, co_prediction, id):
    payload = json.dumps([
        {
            "ref": {
                "id": id,
                "name": "co_j"
            },
            "value": {
                "co_3hb": co_2hb_value,
                "co_2hb": co_1hb_value,
                "co_1hb": co_value
            },
            "deleted": True
        },
        {
            "ref": {
                "id": id,
                "name": "co"
            },
            "value": concentration,
            "deleted": True
        },
        {
            "ref": {
                "id": id,
                "name": "co_pred"
            },
            "value": float(co_prediction[0]),
            "deleted": True
        },

    ])
    return payload

def update_values(model_path, mod_name, co_value, co_1hb_value, co_2hb_value, concentration,token,asset_id):
    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json'
    }

    # Load model and forecast
    co_prediction = pred(load_model(model_path + mod_name), co_value, co_1hb_value, co_2hb_value)
    print("PREDICTION OK...", co_prediction[0])

    # Update values
    payload_update = create_payload(co_2hb_value, co_1hb_value, co_value, concentration, co_prediction, asset_id)
    response = requests.request("PUT", url_put, headers=headers, data=payload_update, verify=False)
    print("DONE!!! ..... Response text:", response.text)

    return co_prediction

def maintenance_warning(maintenance_day, id):
    current_date = datetime.now()
    maintenance_day = text_to_datetime(maintenance_day)
    # Calculate the difference
    time_difference = current_date - maintenance_day
    # Check if more than one year has passed
    if time_difference > timedelta(days=365):
        subject = "Air Guard, Sensor Info"
        email_receiver = receiver
        paragraph = "More than one year has passed since the last maintenance of sensor with id {}.".format(
            id)
        send_email(email_receiver, subject, paragraph)
        return True

    return False

def get_data(url, headers, payload, asset_id):

    asset_info = requests.request("GET", url + asset_id, headers=headers, data=payload, verify=False).text
    data = json.loads(asset_info)

    return data

def send_data():


    while running:
        current_date = datetime.now()
        url = "https://localhost/api/master/asset/"
        payload = {}
        #concentration = random.randint(0, 351)  # pm25
        concentration = random.randint(0, 75)
        #concentration_pm10 = random.randint(0,504)
        concentration_pm10 = random.randint(0, 150)
        #concentration_co = round(random.uniform(0, 40.4), 2)
        concentration_co = round(random.uniform(0, 30.4), 2)
        concentration_co = ppm_to_ugm3(concentration_co,co_molecular_weight)
        #concentration_no2 = random.randint(0,1640)
        concentration_no2 = random.randint(0, 600)
        concentration_no2 = ppb_to_ugm3(concentration_no2,no2_molecular_weight)
        #concentration_ozone = round(random.uniform(0, 0.504), 3)
        concentration_ozone = round(random.uniform(0, 0.350), 3)
        concentration_ozone = ppm_to_ugm3(concentration_ozone,o3_molecular_weight)
        #concentration_so2 = random.randint(0,804)
        concentration_so2 = random.randint(0, 500)
        concentration_so2 = ppb_to_ugm3(concentration_so2,so2_molecular_weight)

        
        token = get_token()
        headers = {
            'Authorization': 'Bearer {}'.format(token)
        }

        # get attribute data FROM PM10
        asset_info = requests.request("GET", url + PM10_ID, headers=headers, data=payload,verify=False).text
        data_pm10 = json.loads(asset_info)
        co_value, co_3hb_value, co_2hb_value, co_1hb_value = get_concentrations(data_pm10)
        maintenance_day = get_value(data_pm10, "MaintenanceDay")
        #maintenance_warning(maintenance_day, PM10_ID)

        # get attribute data FROM PM25
        asset_info2 = requests.request("GET", url + PM25_ID, headers=headers, data=payload, verify=False).text
        data_pm25 = json.loads(asset_info2)
        co2_value, co2_3hb_value, co2_2hb_value, co2_1hb_value = get_concentrations(data_pm25)
        maintenance_day = get_value(data_pm25, "MaintenanceDay")
        #maintenance_warning(maintenance_day, PM25_ID)

        # get attribute data FROM NO2
        asset_info_NO2 = requests.request("GET", url + NO2_ID, headers=headers, data=payload, verify=False).text
        data_no2 = json.loads(asset_info_NO2)
        co_value_no2, co_3hb_value_no2, co_2hb_value_no2, co_1hb_value_no2 = get_concentrations(data_no2)
        maintenance_day = get_value(data_no2, "MaintenanceDay")
        #maintenance_warning(maintenance_day, NO2_ID)

        # get attribute data FROM OZONE
        asset_info_ozone = requests.request("GET", url + OZONE_ID, headers=headers, data=payload, verify=False).text
        data_ozone = json.loads(asset_info_ozone)
        co_value_ozone, co_3hb_value_ozone, co_2hb_value_ozone, co_1hb_value_ozone = get_concentrations(data_ozone)
        maintenance_day = get_value(data_ozone, "MaintenanceDay")
        #maintenance_warning(maintenance_day, OZONE_ID)

        # get attribute data FROM SO2
        asset_info_so2 = requests.request("GET", url + SO2_ID, headers=headers, data=payload, verify=False).text
        data_so2 = json.loads(asset_info_so2)
        co_value_so2, co_3hb_value_so2, co_2hb_value_so2, co_1hb_value_so2 = get_concentrations(data_so2)
        maintenance_day = get_value(data_so2, "MaintenanceDay")
        #maintenance_warning(maintenance_day, SO2_ID)

        # get attribute data FROM CO
        asset_info_co = requests.request("GET", url + CO_ID, headers=headers, data=payload, verify=False).text
        data_co = json.loads(asset_info_co)
        co_value_CO, co_3hb_value_CO, co_2hb_value_CO, co_1hb_value_CO = get_concentrations(data_co)
        maintenance_day = get_value(data_co, "MaintenanceDay")
        #maintenance_warning(maintenance_day,CO_ID)


        token = get_token()

        pm10 = update_values(model_path, mod_pm10, co_value, co_1hb_value, co_2hb_value, concentration_pm10,token,PM10_ID)
        pm25 = update_values(model_path, mod_pm25, co2_value, co2_1hb_value, co2_2hb_value, concentration,token,PM25_ID)
        no2 = update_values(model_path, mod_no2, co_value_no2, co_1hb_value_no2, co_2hb_value_no2, concentration_no2, token, NO2_ID)
        no2 = ugm3_to_ppb(no2,no2_molecular_weight)
        ozone = update_values(model_path, mod_ozone, co_value_ozone, co_1hb_value_ozone, co_2hb_value_ozone, concentration_ozone, token, OZONE_ID)
        print("Predicted ozone",ozone)
        ozone = ugm3_to_ppm(ozone,o3_molecular_weight)
        print("CONVERTED ozone", ozone)
        so2 = update_values(model_path, mod_so2, co_value_so2, co_1hb_value_so2, co_2hb_value_so2,concentration_so2, token, SO2_ID)
        so2 = ugm3_to_ppb(so2,so2_molecular_weight)
        co = update_values(model_path, mod_co, co_value_CO, co_1hb_value_CO, co_2hb_value_CO, concentration_co, token,CO_ID)
        co = ugm3_to_ppm(co,co_molecular_weight)

        ozone_value = turnicate_value(ozone, "OZONE")
        ozone_aqi = calculate_aqi(ozone_value, ozone_breakpoints, ozone_breakpoints_low)

        pm10_value = turnicate_value(pm10, "PM10")
        pm10_aqi = calculate_aqi(pm10_value, pm10_breakpoints, pm10_breakpoints_low)

        pm25_value = turnicate_value(pm25, "PM25")
        pm25_aqi = calculate_aqi(pm25_value, pm25_breakpoints, pm25_breakpoints_low)

        no2_value = turnicate_value(no2, "NO2")
        no2_aqi = calculate_aqi(no2_value, no2_breakpoints, no2_breakpoints_low)

        so2_value = turnicate_value(so2, "SO2")
        so2_aqi = calculate_aqi(so2_value, so2_breakpoints, so2_breakpoints_low)

        co_value = turnicate_value(co, "CO")
        co_aqi = calculate_aqi(co_value, co_breakpoints, co_breakpoints_low)

        aqi = max(pm10_aqi,pm25_aqi,no2_aqi,co_aqi,so2_aqi,ozone_aqi)
        max_aqi_variable = max(
            [(pm10_aqi, 'PM10'), (pm25_aqi, 'PM25'), (no2_aqi, 'NO2'), (co_aqi, 'CO'),
             (so2_aqi, 'SO2'),(ozone_aqi, 'OZONE')])

        print("AQI: %f --> %s because of the %s pollutant" % (aqi,find_aqi_category(aqi),max_aqi_variable[1]))

        print("pm10",pm10_aqi)
        print("pm25",pm25_aqi)
        print("no2",no2_aqi)
        print("co",co_aqi)
        print("so2",so2_aqi)
        print("ozone",ozone_aqi)

        updatenotes(pm10_aqi, PM10_ID, token)
        updatenotes(pm25_aqi, PM25_ID, token)
        updatenotes(no2_aqi, NO2_ID, token)
        updatenotes(co_aqi, CO_ID, token)
        updatenotes(so2_aqi, SO2_ID, token)
        updatenotes(ozone_aqi, OZONE_ID, token)

        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json'
        }

        payload_aqi = json.dumps([
            {
                "ref": {
                    "id": "4UGN9efpeckvB67S7uGDcW",
                    "name": "pollution_level"
                },
                "value": find_aqi_category(aqi),
                "deleted": True
            },
            {
                "ref": {
                    "id": "4UGN9efpeckvB67S7uGDcW",
                    "name": "Index"
                },
                "value": aqi
            }

        ])
        requests.request("PUT", url_put, headers=headers, data=payload_aqi, verify=False)

        times = pm25 / who_guideline

        # OZONE WARNING
        if find_aqi_category(ozone_aqi) in ['Unhealthy for Sensitive Groups', 'Unhealthy', 'Very unhealthy','Hazardous'] :
            paragraph = """
            In the next 2 hours ozone is predicted to be {}. Be careful!!
            Ozone, a key component of oxidant smog, poses a significant threat to plants. 
            Visible leaf symptoms include flecking, bronzing, or bleaching. 
            Yield reductions may occur without visible injury, and some crops can sustain foliar 
            damage without impacting yield. Ground-level ozone hinder photosynthesis, 
            prevent trees and flowers from growing, and delay their blooming.
            Schedule outdoor activities, including watering and fertilization,
            during early morning or late evening when ozone levels are typically lower.
            """.format(ozone_aqi)

            #send_email("mari.tsio@hotmail.com","Ozone concentration very high",paragraph)


        if find_aqi_category(pm25_aqi) in ['Moderate','Unhealthy for Sensitive Groups', 'Unhealthy', 'Very unhealthy','Hazardous']  :
            paragraph = """
            In the next 2 hours pm25 is predicted to be {}. Be careful!!
            
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th style="text-align: center; padding: 8px; border: 1px solid black;">Air pollution level</th>
                    <th style="text-align: center; padding: 8px; border: 1px solid black;">Air quality index</th>
                    <th style="text-align: center; padding: 8px; border: 1px solid black;">Main pollutant</th>
                </tr>
                <tr>
                    <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid black;">PM2.5</td>
                </tr>
            </table>

            The projected PM2.5 concentration in Thessaloniki is expected to be {} times higher than the WHO annual air quality guideline value.
        """.format(pm25_aqi,find_aqi_category(pm25_aqi),pm25_aqi,times)

            print("SENDING FOR PM EMAIL")
           # send_email("mari.tsio@hotmail.com","Important Air Quality Alert: High PM2.5 Levels and Health Recommendations for Thessaloniki",paragraph)

        paragraph = """

                    <table style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <th style="text-align: center; padding: 8px; border: 1px solid black;">Air pollution level</th>
                            <th style="text-align: center; padding: 8px; border: 1px solid black;">Air quality index</th>
                            <th style="text-align: center; padding: 8px; border: 1px solid black;">Main pollutant</th>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">PM2.5</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">PM10</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">OZONE</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">SO2</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">CO</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">{}</td>
                            <td style="text-align: center; padding: 8px; border: 1px solid black;">NO2</td>
                        </tr>
                    </table>
                    
                   <h2> HEALTH RECOMMENDATIONS </h2>
                    <h3>How to protect from air pollution in Thessaloniki?</h3>

                - Sensitive groups should wear a mask outdoors
                - Sensitive groups are suggested to use an air purifier
                - Close your windows to avoid dirty outdoor air
                - Sensitive groups should reduce outdoor exercise
                """.format(find_aqi_category(pm25_aqi), pm25_aqi,find_aqi_category(pm10_aqi),pm10_aqi,find_aqi_category(ozone_aqi),ozone_aqi,
                           find_aqi_category(so2_aqi),so2_aqi,find_aqi_category(co_aqi),co_aqi,find_aqi_category(no2_aqi),no2_aqi)

        # send_email("mari.tsio@hotmail.com",
                 #  "Air Guard Alert: Pollutant Levels and Health Recommendations for Thessaloniki",paragraph)

        print("Waiting for sensor...")
        time.sleep(3600)  # Sleep for some hour


@app.on_event("startup")

def startup_event():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    send_data()

def shutdown(signal, frame):
    global running
    running = False



if __name__ == "__main__":

    uvicorn.run(app, host="localhost", port=8000)

@app.get("/model")
async def root():

    return {"message": "Sending Data...",
            "Flag": "Done"}

