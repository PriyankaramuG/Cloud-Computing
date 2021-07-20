import os
import logging
import math
import random
import queue
import threading
import time
import http.client
import json
import re
import requests
import boto3
import os
import codecs
import csv

from flask import Flask, request, render_template,session
app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY'
app.config['DEBUG'] = True
queue = queue.Queue() # queue is synchronized, so caters for multiple threads



#***************************************************************************************************
#below functions to provision the resources for scalable services
#***************************************************************************************************
import boto3
import os
image_id='ami-0891edf1f41388216'
access_key='AKIAQQECLI6CMZTG2563'
access_secret='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'

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
# Above line needs to be here before boto3 to ensure file is read
ec2 = boto3.resource('ec2',aws_access_key_id=access_key,
         aws_secret_access_key=access_secret)
s3 = boto3.resource('s3',aws_access_key_id=access_key,
         aws_secret_access_key=access_secret)
       
def Create_Instance(instancecount):		
	start = time.time() 
	instance=ec2.create_instances(ImageId='ami-0891edf1f41388216',InstanceType="t2.micro", MinCount=1, MaxCount=instancecount)[0]
	instance.wait_until_running()
	instance.reload()
	instancecreationtime=time.time() - start
	print(instance.state)
	print(instancecreationtime)
	createinsmsg=(str(instancecount)+ " resources successfully provisioned for EC2 with the elapsed time of : " +str(instancecreationtime)+"sec")
	return createinsmsg

def get_runningInstances():
	runningids=[]
	instances = ec2.instances.filter(
	Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
	for instance in instances:
	#print(instance.id, instance.instance_type)
		runningids.append(instance.id)		
	return runningids
	
def get_runningInstances_ip():
	runningidsip=[]
	instances = ec2.instances.filter(
	Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
	for instance in instances:
	#print(instance.id, instance.instance_type)
		
		dnsName=instance.public_dns_name
		ipaddress='http://'+dnsName
		runningidsip.append(ipaddress)
		print(runningidsip)
	return runningidsip	
			
def Terminate_Instance() :
	ids=get_runningInstances()
	print(ids)
	ec2.instances.filter(InstanceIds=ids).terminate()


#***************************************************************************************************
#below class functions used to execute the application within selected scalable services parallely
#***************************************************************************************************
class ThreadUrl(threading.Thread):
	def __init__(self, queue, task_id):
		threading.Thread.__init__(self)
		self.queue = queue
		self.task_id = task_id
		self.data = None # need something more sophisticated if the thread can run many times

	def run(self):
	#while True: # uncomment this line if a thread should run as many times as
	#it can
		shots = self.queue.get()
		rate =self.queue.get()
		sc=self.queue.get()
		
		try:
			#if the selection is EC2, execute the below code which the calls EC2 public IP4 DNS address
			if sc=="EC2":
				print(self.task_id)
				ec2response = requests.get(str(self.task_id)+'/calculatepi.py?shots='+str(shots)+'&rate='+str(rate))
				print(ec2response)
				ec2response = ec2response.text.replace("\'", "\"")
				self.data = ec2response
				
				
            #if the selection is lamda , execute below code which post the request to api gateway
			elif  sc=="Lamda":
				c = http.client.HTTPSConnection("0lzsxrn95l.execute-api.us-east-1.amazonaws.com")
				json= '{ "key1": ' + str(shots) +','+' "key2": ' + str(rate) + '}'
				c.request("POST", "/default/calculatepi", json)
				lamdaresponse = c.getresponse()
				self.data = lamdaresponse.read().decode('utf-8')
		

		except IOError:
			print('Failed to open "%s".' ,  host) # Is the Lambda address correct?

		#signals to queue job is done
		self.queue.task_done()

#***************************************************************************************************
#form post action routs
#***************************************************************************************************
def doRender(tname, values={}):
	if not os.path.isfile(os.path.join(os.getcwd(), 'templates/' + tname)): #No such file
		return render_template('index.htm')
	return render_template(tname, **values) 

# Defines a POST supporting initialise route
@app.route('/warmup', methods=['POST'])
def warmup():
	#warming up the function by passing R=S=D=Q=1
	threads = []
	for i in range(0, 1):
		t = ThreadUrl(queue, i)
		threads.append(t)
		t.setDaemon(True)
		t.start()
	#populate queue with data
	for x in range(0, 1):
		queue.put(int(1))
		queue.put(1)
		queue.put('Lamda')
	return doRender('index.htm',{'lblwarmmsg':'Warm up Completed!'})

# Defines a POST supporting initialise route
@app.route('/initialisevalue', methods=['POST'])
def initialiseHandler():

	if request.method == 'POST':
		
		session.pop('r', default=None)
		session.pop('sc', default=None)
		sc = request.form.get('scalable')
		r = request.form.get('resource')
		session['r']=r
		session['sc']=sc
		print("inside initialize")
		print(session['sc'])
		if sc == '' or r == '':
			 return doRender('index.htm',
					{'note': 'Please select the scalable service and No. of resources!'})
		else:
			s = sc
			IR = int(r)
			runs=IR
			if sc == 'EC2':
				Terminate_Instance()
				createinsmsg=Create_Instance(runs)
				return doRender('input.htm', {'provnote': createinsmsg})
			elif sc =='Lamda':
				return doRender('input.htm')
	return 'Should not ever get here'  

# Defines a POST supporting Input route
@app.route('/calculate', methods=['POST'])
def calculateHandler():
	import http.client
	if request.method == 'POST':
		s = request.form.get('shots')
		q = request.form.get('reportingrate')
		d = request.form.get('digits')
		if s == '' or q == '' or d == '':
			return doRender('input.htm',
					{'note': 'Please enter the inputs!'})
		else: 
			sc=session['sc']
			runs=int(session['r'])
			totalshots=s
			shots=(int(s)/runs)
			rate=int(q)
			isDmet=False
			threads = []
			#created a dictionary to store the list of values receiving from Lamda and EC2
			result=[]
			finalresult=[]
			result={'1ResourceID':[],'3rate':[],'4shots':[],'2incircle':[],'5pivalue':[],'finalpivalue':[],'pi':[],'TotalShots':[],'Totalincircle':[]}
			
			#get the running instances that provisioned
			Dmetloop=1
			while Dmetloop < 11:
				
				if isDmet == True:
					break
				threads = []
				
				finalresult={'1ResourceID':[],'3rate':[],'4shots':[],'2incircle':[],'5pivalue':[],'finalpivalue':[],'pi':[],'TotalShots':[],'Totalincircle':[]}
				
				print(finalresult)
#********************************Execution of EC2**************************************************
				if sc == 'EC2':
					start = time.time()
					time.sleep(10)
					
					ipaddress=get_runningInstances_ip()
					
					for ip in ipaddress:
						t = ThreadUrl(queue, ip)
						threads.append(t)
						t.setDaemon(True)
						t.start()

						#populate queue with data
					for ip in ipaddress:
						queue.put(int(shots))
						queue.put(rate)
						queue.put(sc)

						#enumerating thread
					for index, thread in enumerate(threads):
						thread.join()
						redict = json.loads(thread.data)
						j=0
						#adding the resource information
						for val in redict['1ResourceID']: 
							redict['1ResourceID'][j]="R"+str(index+1)
							j+=1
						#concatenation the data received from the response with resource information
						finalresult={x: finalresult.get(x, 0) + redict.get(x, 0)
												for x in set(finalresult).union(redict)}
					#calculating the cost assuming it for t2.micro
					cost=round((runs* 0.0083 * 1),2)
				
#************************Execution of labda*****************************************
				elif sc == 'Lamda':
					start = time.time()
				#spawn a pool of threads, and pass them queue instance
					for i in range(0, runs):
						
						t = ThreadUrl(queue, i)
						threads.append(t)
						t.setDaemon(True)
						t.start()
				
			
					#populate queue with data
					for x in range(0, runs):
						queue.put(int(shots))
						queue.put(rate)
						queue.put(sc)

					#enumerating thread
					for index, thread in enumerate(threads):
						thread.join()
					
						redict = json.loads(thread.data)
						j=0
						#adding the resource information
						for val in redict['1ResourceID']: 
							redict['1ResourceID'][j]="R"+str(index+1)
							j+=1
						
						#concatenation the data received from the response with resource information
						finalresult={x: finalresult.get(x, 0) + redict.get(x, 0)
												for x in set(finalresult).union(redict)}
				
				result={x: result.get(x, 0) + finalresult.get(x, 0)
												for x in set(result).union(finalresult)}
				 

				#calculating the final D
				print("2incircele")
				print(totalshots)
				print(sum(result['2incircle']))
				FinalD=4*sum(result['2incircle'])/int(totalshots)
				actpi_dig = 1
				DinPi = list()
				for x in str(math.pi):
					actpi_dig += 1
					DinPi.append(x)
					if actpi_dig == int(d)+2:
						break

				actpi_dig = ''.join(DinPi)
			
				#check if Final D is met 
				if(str(actpi_dig) in str(FinalD)):
					finalpi=FinalD
					FinalD="final D is met : expected=", actpi_dig ,", estimated= ",FinalD
					isDmet=True	
				else :
					finalpi=FinalD
					FinalD="final D is not met with 10 s : expected=", actpi_dig ,", estimated= ",FinalD
					isDmet=False
					
				totalshots=int(totalshots)
				totalshots+=int(s)
				Dmetloop+=1
			
			#sorting the dictionary as it was rendering different column every time
			dict(sorted(result.items()))
			result['ResourceID'] = result.pop('1ResourceID')
			result['incircle'] = result.pop('2incircle')
			result['rate'] = result.pop('3rate')
			result['shots'] = result.pop('4shots')
			result['pivalue'] = result.pop('5pivalue')

			dict(sorted(finalresult.items()))
			finalresult['ResourceID'] = finalresult.pop('1ResourceID')
			finalresult['incircle'] = finalresult.pop('2incircle')
			finalresult['rate'] = finalresult.pop('3rate')
			finalresult['shots'] = finalresult.pop('4shots')
			finalresult['pivalue'] = finalresult.pop('5pivalue')

			#preparing data for chart

			temp=0
			concatincircle=[]
			concatshots=[]
			concatpi=[]
			for val in finalresult['incircle']:
				temp+= val
				concatincircle.append(temp)
			i=1
			for val in finalresult['shots']:
				temp= val*i
				concatshots.append(temp)
				i+=1
			
			for count in range(len(concatshots)):
				concatpi.append(4*(concatincircle[count]/concatshots[count]))   
			totalpivalueToStr = ','.join([str(elem) for elem in concatpi])
			totalshotsToStr = ','.join([str(elem) for elem in concatshots])
			pivalueToStr = ','.join([str(elem) for elem in finalresult['pi']])
			chartdata=totalpivalueToStr+'|'+pivalueToStr
			#preparing data for chart completed
			#Elapsed Time
			elaspsedtime=round(time.time() - start,3)
			#calculation of cost
			if(sc == 'Lamda' ):
				print("cost for lambda")
				cost=round((runs* elaspsedtime )*128/1024,2)
			#time.sleep(5)
			totsh=int(totalshots)-int(s)
			#with open('HistorySystem.csv', 'a', newline='') as csvfile:
				#writer = csv.writer(csvfile, delimiter=' ',
                            #quotechar='|', quoting=csv.QUOTE_MINIMAL)
				#writer.writerow([s,rate,runs,d,finalpi,cost,Dmetloop-1,totsh,sc])
			
			return doRender('output.htm',{'result': finalresult,'FinalD':FinalD,
								 'shots':totsh,'rate':rate,'Noofrounds':Dmetloop-1,'NoResource':runs,'nodigits':d,'ElapsedTime':elaspsedtime,'chartdata':chartdata,'scalservice':sc,'cost':cost})
			#return doRender('input.htm',{'results': results})
	return 'Should not ever get here'

	
# Defines a POST supporting output route
# clearing the resource and scalable information session values
@app.route('/Termination', methods=['POST'])
def outputHandler():
	#clear the session value
	
	print("inside output")
	print(session['sc'])
	Terminate_Instance()
	time.sleep(5)
	return render_template('Termination.htm')
	
@app.route("/History",methods = ['POST', 'GET'])
def History():
	if request.method == 'POST':
		print("in post method")
		bucket = s3.Bucket(u'historypi')
		obj = bucket.Object(key=u'HistorySystem.csv')
		response = obj.get()
		History=[]
		for row in csv.DictReader(codecs.getreader("utf-8")(response["Body"]),delimiter=' ', quotechar='|'):
			History.append({
		"Shots": row['Shots'],
		"Reporting_Rate": row['ReportingRate'],
		"No_of_Resources": row['Resources'],
		"Digits": row['Digits'],
		"Pi_value": row['Pivalue'],
		"cost": row['cost'],
		"runs": row['runs'],
		"TotalShots": row['TotalShots'],
		"ScalableService": row['ScalableService'],
		
		
		})
		return render_template("History.htm", History=History)
	return render_template("History.htm")
#app.add_url_rule("/History","History",History)  
# catch all other page requests - doRender checks if a page is available (shows
# it) or not (index)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def mainPage(path):
	return doRender(path)

@app.errorhandler(500)
# A small bit of error handling
def server_error(e):
	logging.exception('ERROR!')
	return """
	An  error occurred: <pre>{}</pre>
	""".format(e), 500

if __name__ == '__main__':
	# Entry point for running on the local machine
	# On GAE, endpoints (e.g.  /) would be called.
	# Called as: gunicorn -b :$PORT index:app,
	# host is localhost; port is 8080; this file is index (.py)
	app.run(host='127.0.0.1', port=8080, debug=True)

