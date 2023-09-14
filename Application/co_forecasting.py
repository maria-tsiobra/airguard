import pickle
import time
import xgboost as xgb
import pandas as pd
import numpy as np
import sklearn

def load_model(model_path):
    model = xgb.XGBRegressor()
    # Load the trained model
    model = pickle.load(open(model_path, 'rb'))
    print("LOADING MODEL OK...")
    feature_names = model.get_booster().feature_names
    #print("Waiting features",feature_names)
    return model

def transform_features(prev_1hours,prev_2hours, prev_3hours):
    """
    features=['seg_hour', 'day', 'month', 'weekday',
       'year','weekend', 'day/night',"prev_2hours",
       'prev_two_hours_mean', 'prev_two_hours_min', 'prev_two_hours_max',
       'prev_three_hours_mean', 'prev_three_hours_min',
       'prev_three_hours_max']
    """
    t = time.time() + 7200

    now_time = pd.to_datetime(t, unit='s')

    # Create an array for each feature
    seg_hour = now_time.hour
    day = now_time.day
    month = now_time.month
    weekday = now_time.weekday()
    year = now_time.year
    weekend = 1 if weekday in [5, 6] else 0
    day_night = 1 if seg_hour < 18 and seg_hour > 6 else 0
    prev_2hours_mean = (prev_1hours + prev_2hours) /2
    prev_2hours_min = min(prev_1hours , prev_2hours)
    prev_2hours_max = max(prev_1hours , prev_2hours)
    prev_3hours_mean = (prev_3hours + prev_2hours) /2
    prev_3hours_min = min(prev_3hours , prev_2hours)
    prev_3hours_max = max(prev_3hours , prev_2hours)

    # Concatenate the features
    features = [
        seg_hour, day, month, weekday, year, weekend, day_night,prev_2hours,
        prev_2hours_mean, prev_2hours_min, prev_2hours_max,
        prev_3hours_mean, prev_3hours_min, prev_3hours_max
    ]

    return features

def pred(model,prev_1hours, prev_2hours, prev_3hours):
    # function to make predictions
    x = transform_features(prev_1hours,prev_2hours, prev_3hours)
    #print("FEATURES",x)
    f = np.array(x).reshape(1, -1)
    # Perform the prediction using the loaded model
    concentration = model.predict(f)
    return concentration.round(1)
