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

LOGS_DIR = Path(str(DATA_DIR) + "/logs")
if not LOGS_DIR.is_dir():
	LOGS_DIR.mkdir()

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
		"text": "",
	},
	
	"log_level": 1,
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

class logger:
	def __init__(self, log_level: int = 1, log_file_path: Path | str = "default"):
		self.log_level = log_level
		
		if isinstance(log_file_path, str):
			if log_file_path == "default":
				log_file_path = Path(str(LOGS_DIR)+'/'+time.strftime("%Y-%m-%d", time.localtime()))
			else:
				log_file_path = Path(str(LOGS_DIR)+'/'+log_file_path)
		
		self.log_file_path = Path(log_file_path)
	
	log_levels = [
		"DEBUG",
		"INFO",
		"WARNING",
		"ERROR",
	]
	
	def new(self, log_level: int = 0, text: str = "", save_to_file: bool = True):
		if log_level >= self.log_level:
			level_str = self.log_levels[log_level].upper()
			log_txt = f"[{level_str}] {text}"
			print(log_txt)
			
			if save_to_file:
				with self.log_file_path.open('w', encoding='utf-8') as log_file:
					log_file.write(log_txt + '\n')

def main():
	settings = data.get_settings()
	
	main_logger = logger(settings.get('log_level') if settings.get('log_level') else 1)
	
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
					main_logger.new(1, f"Data has been update! URL: {settings['url']}")
					
					TGbot = settings.get('TGbot')
					if TGbot:
						if TGbot.get('enabled'):
							success = False
							try:
								token = str(TGbot['token'])
								chatId = int(TGbot['chatId'])
								success = True
							except IndexError:
								main_logger.new(4, "Invalid Telegram bot settings.")
							except Exception as e:
								main_logger.new(4, f"An unknown error occurred while retrieving critical data to send a message to Telegram: {e}.")
							
							if success:
								text = TGbot.get('text')
								if not text:
									text = f"New data!\nSee {settings['url']} for more information." # Default text
								
								TelegramAPI.sendMessage(token, chatId, text)
							else:
								main_logger.new(3, "The Telegram message wasn`t sent.")
				else:
					main_logger.new(1, "The data hasn`t been updated", False)
			else:
				try:
					time.sleep((settings['updateTime'] - elpased_time) // 1000000 + 1)
				except KeyboardInterrupt:
					main_logger.new(1, "The user caused the stop", False)
					exit()
		else:
			cycle(settings['url'])

main()
