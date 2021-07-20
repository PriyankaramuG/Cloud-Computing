import math
import random
import json
def lambda_handler(event, context):
    
    values={'ResourceID':[],'rate':[],'shots':[],'incircle':[],'pivalue':[],'finalpivalue':[],'pi':[],'TotalShots':[],'Totalincircle':[]}
   
    totalincircle=0
    shotsout=0
    shots = int(event['key1'])
    rate = int(event['key2'])
    perQ=int(shots/rate)
    for s in range(perQ):
       incircle = 0
       sh=rate
       for i in range(1, sh+1):
          random1 = random.uniform(-1.0, 1.0)
          random2 = random.uniform(-1.0, 1.0)
          if( ( random1*random1 + random2*random2 ) < 1 ):
              incircle += 1
       
       totalincircle+=incircle
     
       shotsout+=rate
       pivalue=4*(incircle/sh)
       finalpivalue=4*(totalincircle/shotsout)
       values['ResourceID'].append("R0")
       values['rate'].append(sh)
       values['shots'].append(i)
       values['incircle'].append(incircle)
       values['pivalue'].append(pivalue)
       values['finalpivalue'].append(finalpivalue)
       values['pi'].append(math.pi)
       values['TotalShots'].append(shotsout)
       values['Totalincircle'].append(totalincircle)
      
   
    return(values)
