from pathlib import Path
import requests
import time
import hashlib

import json5

SCRIPT_FILE = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_FILE.parent

DATA_DIR = Path(str(SCRIPT_DIR) + "/data")
if not DATA_DIR.is_dir():
	DATA_DIR.mkdir()

SETTINGS_PATH = Path(str(DATA_DIR) + "/settings.json5")
LAST_UPDATE_DATA__PATH = Path(str(DATA_DIR) + "/.lastUpdData")

class data:
	@staticmethod
	def get_settings():
		if SETTINGS_PATH.is_file():
			with SETTINGS_PATH.open('r', encoding='utf-8') as settings_file:
				settings = json5.parse(settings_file.read())[0]
		else:
			settings = r"""{
	"url": "https://github.com/",
	"updateTime": 43200000000,
	"TGbot": {
		"enabled": false,
		"token": "",
		"chatId": 0,
		"text": "New news!\nSee https://github.com/ for more information.",
	},
}"""
			
			with SETTINGS_PATH.open('w', encoding='utf-8') as settings_file:
				settings_file.write(settings)
			settings = json5.parse(settings)[0]
		
		return settings
	
	@staticmethod
	def get_lastUpdateData():
		lastUpdateData = {}
		if LAST_UPDATE_DATA__PATH.is_file():
			with LAST_UPDATE_DATA__PATH.open('rb') as lastUpdateData_file:
				lastUpdateData['hash'] = lastUpdateData_file.read(32)
				lastUpdateData['time'] = int(lastUpdateData_file.read(8).hex(), 16)
				lastUpdateData['success'] = True
		else:
			# Create file
			with LAST_UPDATE_DATA__PATH.open('wb'):
				pass
			
			lastUpdateData['success'] = False
		
		return lastUpdateData
	
	@staticmethod
	def update_lastUpdateData(hash: bytes, time: bytes | int):
		if len(hash) != 32:
			raise ValueError
		
		if isinstance(time, int):
			time = time.to_bytes(8)
		elif isinstance(time, bytes) and len(time) != 8:
			raise ValueError
		
		# Update file
		with LAST_UPDATE_DATA__PATH.open('wb') as lastUpdateData_file:
			lastUpdateData_file.write(hash + time)

class TelegramAPI:
	@staticmethod
	def sendMessage(token, chatId, text):
		url = f"https://api.telegram.org/bot{token}/sendMessage"
		requests.post(url, data={'chat_id': chatId, 'text': text, "parse_mode": "Markdown"})

def main():
	settings = data.get_settings()
	
	def cycle(url):
		response = requests.get(url, headers={})
		hashOfResponse = hashlib.sha3_256(response.content).digest()
		
		data.update_lastUpdateData(hashOfResponse, time.time_ns())
		return hashOfResponse
	
	while True:
		lastUpdateData = data.get_lastUpdateData()
		if lastUpdateData.get('success'):
			elpased_time = time.time_ns() - lastUpdateData['time']
			if elpased_time >= settings['updateTime']:
				if cycle(settings['url']) != lastUpdateData['hash']:
					print(f"Data has been update!\n\turl: {settings['url']}")
					
					TGbot = settings.get('TGbot')
					if TGbot:
						if TGbot.get('enabled'):
							try:
								token = str(TGbot['token'])
								chatId = int(TGbot['chatId'])
								text = str(TGbot['text'])
							except Exception:
								print("[WARNING] Invalid Telegram bot settings")
							TelegramAPI.sendMessage(token, chatId, text)
			else:
				time.sleep((settings['updateTime'] - elpased_time) // 1000000 + 1)
		else:
			cycle(settings['url'])

main()
