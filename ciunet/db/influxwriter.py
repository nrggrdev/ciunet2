import datetime
import time
from influxdb import InfluxDBClient
class influxWriter():
    def __init__(self,config):
        host=config["host"]
        port=config["port"]
        name=config["name"]
        self.devicestatus_table=config["devicestatus_table"]
        pass
        self.offline=False
        print('***INFLUX***')
        self.client = InfluxDBClient(host=host, port=port, retries=1, timeout=1, database=name)

        try:
            print(self.client.ping())
        except:
            self.offline =True

    def receiveStatusData(self,devicedata,sender):
        if self.offline:return
#        print("Hallo",sender,"test", devicedata)
        json_body = []
        try:
            utc_datetime = datetime.datetime.now()
            t = utc_datetime.astimezone()
            analog_keys = (devicedata['analog_ins'].keys())
            analog_values = (devicedata['analog_ins'].values())
            anas = {}
            for i, element in enumerate(analog_values):
                anas.update({f'Ana{i}': element['value']})

            data = {
                "measurement": self.devicestatus_table,
                "tags": {
                    "typeId": "analog-input",
                    "unit": "mV",
                    "source": sender,
                },
                "time": t,
                "fields": anas
            }

            json_body.append(data)

 #           print("Trying to write to db")
  #          print(json_body)
            self.client.write_points(json_body)
   #         print("{} : Data written to DB for event {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), event))

        except Exception as e:
            print("{} : Error: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), e))