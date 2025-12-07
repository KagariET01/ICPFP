
import json
import os
import pathlib

if(pathlib.Path("secret.json").exists()):
	pass
else:
	llm_apikey=input("Enter your OpenAI API Key: ").strip()
	dc_apikey=input("Enter your Discord Bot Token: ").strip()

	f=open("secret.json","w+")
	f.write(json.dumps({"llm_apikey":llm_apikey,"dc_apikey":dc_apikey}))
	f.close()

if(os.system("docker --version")):
	print("Docker is not installed or not in PATH. Please install Docker and ensure it's in your system PATH.")
	exit(1)

os.system("docker image rm dchatgpt -f || true")
os.system("docker build -t dchatgpt --no-cache .")
os.system("docker rm dchatgpt_container -f || true")
os.system("docker run -d --name dchatgpt_container dchatgpt")