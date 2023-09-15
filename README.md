# airguard
Air Guard an air pollution forecasting and monitoring project using IoT platform (Open Remote).
To monitor the air pollution six pollutants has been used, Carbon Monoxide ,Nitrogen Dioxide, 
Ozone, Particulate Matter 10, Particulate Matter 25 and Sulfur Dioxide. 
Precise forecasts are made by using XGBoost algorithm to built the ML model. The acquired predicted values are
then used to calculate the Air Quality Index (AQI), providing a standardized way to calculate
the quality of air. Email notification functionality has been developed to enable automated
alerts when the AQI reaches a predefined levels.

Prerequisites:
To run the docker image from Docker Hub, Docker is needed to be installed.
To run the notebooks Python is needed.

**Getting Started with docker image:**

To run this Docker image (which is folder AirGuard), follow these steps:

1. *Clone the Repository*
2. *Navigate to the Project Directory*
3. *Use the following commands: *
    docker-compose pull
    docker-compose -p openremote up

**Forecasting**
A forecasting model using the XGBoost algorithm. The data preprocessing steps carried out on the dataset prior to 
training are shown in Fortecasting folder, one model for each pollutant.

**Data**
The data used in this study is sourced from the European Environment Agency's (EEA) air quality database.

**Application**
The application folder contains the connection between the OpenRemote platform and the dumy sensors. Also there is a module responsible for sending the emails and one converting the input data to apropriate format for the forecasting model.
