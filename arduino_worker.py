
import multiprocessing
from multiprocessing import Queue, Manager
from threading import Lock
import serial
from dto_classes import ResourceAllocationDto, ResourceResponseDto
#from typing import Self
from fastapi import status
import logging
import requests
import json
import time
from datetime import datetime

log = logging.getLogger(__name__)
resources = Manager().dict({"R_TEMP":  False,
             "R_BUILT_IN_LED": False
            })
class ArduinoWorker(multiprocessing.Process):

    def __init__(self):
        super().__init__()
        self.allocated_resource = {}
        self.allocation_queue = Queue()    
        self.messageType = None
        self.length = None

    def setup(self, arduino_id: str, user_name: str, password:str, serial_port: str, baudrate: int):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.arduino_id = arduino_id
        self.user_name = user_name
        self.password = password
        self.ser = serial.Serial(self.serial_port,self.baudrate)

    def allocate_resource(self, dto: ResourceAllocationDto) -> status:
        log.debug('Got resource allocation request')
        if not (dto.resource in list(resources.keys())):
            return status.HTTP_404_NOT_FOUND
        self.allocation_queue.put(dto)
        return status.HTTP_202_ACCEPTED

    def run(self):
        log.debug('Starting worker')
        time.sleep(1)
        self.ser.read(self.ser.inWaiting())
        while True:
            # Checks if no message is in the pipe.
            if self.messageType is None:
                # Checks if all bytes for the type and length has arrived.
                if self.ser.inWaiting() >= 3:
                    # Reads the messageType (first byte) and the message length (next two bytes) and stores them as integers.
                    type = self.ser.read(1)
                    self.messageType = int(str(type,'utf-8'))
                    self.length = int(str(self.ser.read(2),'utf-8'))

            # Checks if a message is in the pipe.
            if self.messageType is not None:
                # Checks if all bytes for the message has arrived.

               if self.ser.inWaiting() >= 3:
                    # Reads the messageType (first byte) and the message length (next two bytes) and stores them as integers.
                    type = self.ser.read(1)
                    self.messageType = int(str(type,'utf-8'))
                    self.length = int(str(self.ser.read(2),'utf-8'))

            # Checks if a message is in the pipe.
            if self.messageType is not None:
                # Checks if all bytes for the message has arrived.
                if self.ser.inWaiting() >= self.length:
                    # Reads the message.
                    message = self.ser.read(self.length)
                    # Sends the message to the response handler as a string with extra null bytes removed.
                    self.handleArduinoResponse(str(message,'utf-8').rstrip('\x00'))

                    # Setting the message as handled by setting the message type and length to None.
                    self.messageType = None
                    self.length = None
            try:
                dto = self.allocation_queue.get(timeout=2)
                self.register_resource_allocation(dto)
            except Exception as e:
                pass

    def register_resource_allocation(self, dto: ResourceAllocationDto) -> None:
        log.debug(f'Registering a resource allocation {dto.resource}.')

        self.allocated_resource[dto.resource] = (dto,{})

       if dto.resource == "R_BUILT_IN_LED":
            self.allocated_resource[dto.resource][1]['start_time'] = datetime.now()
            self.sendInstructions(1,json.loads(dto.parameter)["frequency"])
        elif dto.resource == "R_TEMP":
            self.allocated_resource[dto.resource][1]['start_time'] = datetime.now()
            self.allocated_resource[dto.resource][1]['timestamp'] = []
            self.allocated_resource[dto.resource][1]['temperature'] = []
            self.sendInstructions(2, json.loads(dto.parameter)["frequency"])
            # TODO: skicka instruktioner till Arduinon...

    def handleArduinoResponse(self, message):
        log.debug(f"Got message: from Arduino Type:{self.messageType}, Message: {message}")
        # Handles messages of type temperature collection.
        current_time = datetime.now()
        if self.messageType == 1:
            if "R_BUILT_IN_LED" not in self.allocated_resource:
                log.warning('Got built in LED is enabled but not requested.')
                return
            if (current_time-self.allocated_resource["R_BUILT_IN_LED"][1]['start_time']).total_seconds() > json.loads(self.allocated_resource["R_BUILT_IN_LED"][0].parameter)["duration$
                self.sendResult(self.allocated_resource["R_BUILT_IN_LED"][0].request, {})
                self.sendInstructions(1,0)
                del self.allocated_resource["R_BUILT_IN_LED"]

        elif self.messageType == 2:
            temperature = float(message)
            if "R_TEMP" not in self.allocated_resource:
                log.warning('Got temperature that was not requested.')
                return
            self.allocate_resource["R_TEMP"][1]['timestamp'].append(
                current_time.strftime("%Y-%m-%d %H:%M:%S")

               )
            self.allocate_resource["R_TEMP"][1]['temperature'].append(
                temperature
                )
            # mTODO Spara temperaturen och tiden (append) i self.allocated_resource["R_TEMP"][1]
            if (current_time-self.allocated_resource["R_TEMP"][1]['start_time']).total_seconds() > json.loads(self.allocated_resource["R_TEMP"][0].parameter)["duration"]:
                output = {"timestamp": self.allocated_resource["R_TEMP"][1]['timestamp'],
                          "temperature": self.allocated_resource["R_TEMP"][1]['temperature']}

                self.sendResult(self.allocated_resource["R_TEMP"][0].request, output)
                self.sendInstructions(2,0)

                del self.allocated_resource["R_TEMP"]

    def sendResult(self, request_id, output):

        result = {"requestId": request_id,
                    "arduinoId": self.arduino_id,
                    "result": json.dumps(output)}
        log.debug(f"Sending result to middleware. {result}")
        r = requests.put('https://tnk116.kts.itn.liu.se/services/result', auth=(self.user_name,self.password), json=result)
        if r.status_code != 200:
            log.warning(f'Failed to send result status code: {r.status_code}')

    def sendInstructions(self, messageType: int, value):
        value = str(value)
        # Sends the TLV message to the Arduino as a string.
        payload = "{}{:02}{}".format(messageType,len(value),value).encode()
        log.debug(f'Sending instructions to Arduino: {payload}.')
        self.ser.write(payload)
