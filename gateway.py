#!/usr/bin/python
import logging
import sys
import secrets
import os
from dotenv import load_dotenv
#from typing import Annotated
import uvicorn
from fastapi import FastAPI, Response, status, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import multiprocessing
from arduino_worker import ArduinoWorker
from dto_classes import ResourceAllocationDto

log = logging.getLogger(__name__)
app = FastAPI()
worker = ArduinoWorker()


@app.put("/resource")
async def allocate_resource(dto: ResourceAllocationDto, response: Response):
    
    status_code = worker.allocate_resource(dto)
    response.status_code  = status_code
#     match status_code:
#          case status.HTTP_404_NOT_FOUND:
#             log.info(f'Resource {dto.resource} not found')
#             return f'Resource {dto.resource} not found'
#          case status.HTTP_503_SERVICE_UNAVAILABLE:
#             log.info(f'Resource {dto.resource} is already in use')
#             return f'Resource {dto.resource} is already in use'
#          case status.HTTP_202_ACCEPTED:
#             log.info("Allocated resource %s (%s)", dto.resource, dto.request)
#             return f'Resource {dto.resource} is allocated in use'
    if status_code == HTTP_404_NOT_FOUND:
        log.info(f'Resource {dto.resource} not found')
        return f'Resource {dto.resource} not found'
    elif status_code == HTTP_503_SERVICE_UNAVAILABLE:
        log.info(f'Resource {dto.resource} is already in use')
        return f'Resource {dto.resource} is already in use'

        return f'Resource {dto.resource} is already in use'
    elif status_code == HTTP_202_ACCEPTED:
        log.info("Allocated resource %s (%s)", dto.resource, dto.request)
        return f'Resource {dto.resource} is allocated in use'
    
if __name__ == '__main__':
    # variables from .env file
    load_dotenv()

    level = getattr(logging,os.getenv('LOG_LEVEL','INFO').upper())
    logging.basicConfig(level=level, format="[%(asctime)s %(levelname)s %(name)s: %(message)s]")
    multi_log = multiprocessing.get_logger()
    formatter = logging.Formatter('[%(asctime)s %(levelname)s %(name)s/%(processName)s]: %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    multi_log.addHandler(handler)
    multi_log.setLevel(level)

    
    log.info("Starting...")
    worker.setup(os.getenv('ARDUINO_ID'), os.getenv('USER_NAME'), os.getenv('PASSWORD'), os.getenv('SERIAL_PORT','/dev/ttyACM0'), os.getenv('BAUDRATE','9600'))
    worker.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
    sys.exit(0)
