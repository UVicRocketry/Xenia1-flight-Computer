from rocket_data import RocketData as rd
import csv

class SendData:
    """
    This only deals with sending the rocketdata. RocketData class in src/rocketData.py deals with manipulating the data.

    ...

    Attributes
    ----------
    rocket_data
        protected attribute that holds all the sensor rocket data imported from rocketData

    Methods
    -------
    send_bme(self, sendingTo)
        Description:
            only called in send_all
        Parm:
            sendingTo can either be "blackbox", "antenna"

    send_imu(self, sendingTo)
        Description:
            only called in send_all
        Parm:
            sendingTo can either be "blackbox", "antenna"

    send_strain_gauges(self, sendingTo)
         Description:
            only called in send_all
        Parm:
            sendingTo can either be "blackbox", "antenna"

    send_all_data(self, sendingTo)
        Description:
            For sending to blackbox: Calls convert_to_csv to get a list of all the data and saves it to a csv
        Parm:
            sendingTo can either be "blackbox", "antenna"
            destination: the name of the csv file to save to

    format_to_send(self, sendingTo)
        Description:
            formats the data into a sendable state
        Parm:
            sendingTo: can either be "blackbox", "ground"
            dataToFomat: Which sensor is needed to be called
    -------
    """
    def __init__(self, rd):
        self.rocket_data = rd

    # TODO: parm rd is a dict of updated
    def update_rocket_data(self, rocket_data):
        self.rocket_data = rd.data_dict_set(rocket_data)

    # TODO: Methods should only do one thing. It would probably be easier if
    #       we just had one method for each destination. Also this will lead to
    #       many bugs where there is a slight typo in the name of the destination
    #       and this method does not report any errors if the name is not found.
    def send_all_data(self, sending_to, destination):
        if sending_to == 'blackbox':
            data = self.rocket_data.convert_to_csv()
            f = open(destination, 'a')
            writer = csv.writer(f)
            writer.writerow(data)
            f.close()