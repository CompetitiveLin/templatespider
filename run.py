from scrapy.cmdline import execute
import sys
import os
import time
website = 'havenly'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
t = int(time.time()*1000)
execute(("scrapy crawl "+str(website)).split())
# execute(("scrapy crawl "+str(website)+" -s LOG_FILE = log/"+website+"_"+str(t)+".log").split())
