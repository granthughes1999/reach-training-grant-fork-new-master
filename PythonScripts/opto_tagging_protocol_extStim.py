# -*- coding: utf-8 -*-
"""
Created on Sat Oct  4 08:37:43 2025

@author: christielab
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial
 
def optotagging_protocol(port="COM5", interval=2, duration=120):
    try:
        ser = serial.Serial('COM5', write_timeout = 0.001)
        print("-------Stim Serial Connected--------")                                    
    except Exception as e:
        print('No Stim serial')
        print(e)
            
    n_pulses = duration // interval
    print(f"Starting optotagging: {n_pulses} pulses, every {interval} sec")
     
    for i in range(n_pulses):
        try:
            msg = 'x'
            print(f"Pulse {i+1}/{n_pulses} sent")
            ser.write(msg.encode())
        
        except Exception as e:
            print(e)
        time.sleep(interval)
    ser.close()
    print("Optotagging complete.")

if __name__ == "__main__":
    optotagging_protocol(port="COM5", interval=2, duration=120)


