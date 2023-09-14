import math

AQI_values = [50, 100, 150, 200, 300, 400, 500]


def turnicate_value(value, pollutant):
    result = None
    if pollutant == "OZONE":
        result = math.floor(value * 10 ** 3) / 10 ** 3
    elif pollutant == "PM25" or pollutant == "CO":
        result = math.floor(value * 10 ** 1) / 10 ** 1
    elif pollutant == "PM10" or pollutant == "SO2" or pollutant == "NO2":
        result = int(value)

    return result


def calculate_aqi(truncated_value, breakpoints, breakpoints_low):

    # Find the range of breakpoints that the value falls between
    lower_index = 0
    upper_index = 0

    for i in range(len(breakpoints)-1):
        if breakpoints[i] <= truncated_value:
            lower_index = i
        if breakpoints[i] >= truncated_value:
            upper_index = i
            break

    if lower_index != 6:
        bp_lo = breakpoints_low[lower_index+1]
    else:
        bp_lo = breakpoints_low[lower_index]
    bp_hi = breakpoints[upper_index]
    aqi_lo = AQI_values[lower_index] + 1
    aqi_hi = AQI_values[upper_index]

    # Calculate the index value using the equation
    index_value = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (truncated_value - bp_lo) + aqi_lo

    return round(index_value)
