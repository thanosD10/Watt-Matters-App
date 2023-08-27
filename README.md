# RUN APPLICATION STEP BY STEP
## Docker

 1. Install Docker and Docker Compose

 2. Open a terminal and navigate to the directory containing the docker-compose.yml file. 
    
3. Start the Docker Compose by running the following command:

    ```bash
    docker-compose --env-file .env up --build
    ```    

4. Verify if both your Docker containers are running by executing the following command:

    ```bash
    docker ps
    ```
5. To stop the Docker Compose and remove the containers, use Ctrl+C in the terminal where you started the docker-compose up command and then run the command:

    ```bash
    docker-compose down
    ```

Docker containers has started!


## InfluxDB

Update file named .env with your InfluxDB USERNAME and PASSWORD.

   * InfluxDB service is available at http://localhost:8086.
   * The credentilas for signing in are the same as those defined in the .env file.


## MQTT Publisher

Start the MQTT Publisher by running the command:

```bash
python smart_sensor.py
```


## Run App Frontend

Start the Application frontend by running the command:

```bash
python watt_matters_app.py
```

.

.

Enjoy!
