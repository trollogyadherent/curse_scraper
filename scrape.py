#!/usr/bin/python3

import argparse
import json
import os
import pprint
import sys

from bs4 import BeautifulSoup
import cloudscraper
import requests


base_url = 'https://www.curseforge.com/minecraft/mc-mods?filter-game-version=2020709689:4449&filter-sort=1' #&page=1'
api_base_url = 'https://api.curse.tools/v1/cf'
progress_file = 'progress.txt'
print('progress file set to: ' + progress_file)
game_version = '1.7.10'

counter = 1
max_pages = None

user_agent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0; Trident/5.0)'

scraper = cloudscraper.create_scraper(delay=10,   browser={'custom': user_agent,})


minecraft_game_id = None

def main():
	global progress_file
	global api_base_url
	global game_version
	global user_agent

	global_json = 'info.json'
	user_agent = ''

	parser = argparse.ArgumentParser(description='CurseForge Minecraft 1.7.10 mod scraper.')

	parser.add_argument('-d', '--downloads', type=str, help="location of downloaded files")
	parser.add_argument('-p', '--progress', type=str, help="location of the progress file")
	parser.add_argument('-a', '--api', type=str, help="Curse proxy, curse.tools used by default")
	args = parser.parse_args()

	download_location = 'downloads'

	if args.progress:
		progress_file = args.progress
	if args.api:
		api_base_url = args.api
	if args.downloads:
		download_location = args.downloads

	current_page = None
	#print(f'amount of pages: {amount_of_pages}')
	
	if os.path.exists(progress_file):
		print('Progress file detected')
		if yes_or_no('Do you wish to resume?'):
			current_page = int(get_last_page_from_progress_file())
		else:
			print('Fetching number of pages...')
			current_page = int(get_amount_of_pages())
			os.remove(progress_file)
	else:
		current_page = int(get_amount_of_pages())

	data = {}
	if os.path.exists(global_json):
		data= json.load(global_json)

	while(current_page >= 1):
		print('Downloading page ' + str(current_page))
		save_mod_page_progress(str(current_page))
		ids = get_ids_for_page(str(current_page))
		if len(ids) == 0:
			die('Failed to get ids for page ' + str(current_page))
		for id_ in ids:
			json_ = get_json_for_modid(id_)
			if json_ is None:
				continue
			print('Downloading ' + json_['data']['name'])
			file_id = get_file_id_from_json(json_)
			file_url = get_file_url_from_json(json_)
			if file_id is None or file_url is None:
				print('Warning! No files found for ' + str(id_) + '!')
				continue
			data[id_] = json_
			mod_location = os.path.join(download_location, str(id_))
			file_location = os.path.join(mod_location, str(file_id))
			if not os.path.exists(mod_location):
				os.makedirs(mod_location)
			if not os.path.exists(file_location):
				os.makedirs(file_location)
			file_json = get_file_json(id_, file_id)
			file_json_location = os.path.join(file_location, 'info.json')
			complete_file_location = os.path.join(file_location, file_json['data']['fileName'])
			write_JSON(file_json, file_json_location)
			if not os.path.exists(complete_file_location):
				r = requests.get(file_url, allow_redirects=True, headers={'User-Agent': user_agent})
				open(complete_file_location, 'wb').write(r.content)
			else:
				print('File already downloaded, skipping')
		current_page -= 1
	
	#print(get_file_url_from_json(get_json_for_modid(53686)))

	write_JSON(data, os.path.join(download_location, global_json))

def get_json_for_modid(modid):
	url = api_base_url + '/mods/' + str(modid)
	response = requests.get(url)
	if response is None or response.status_code != 200:
		print("Couldn't get json for mod id " + str(modid))
		return None
	return response.json()

def get_file_id_from_json(json_):
	latest_files_indexes = json_['data']['latestFilesIndexes']
	file_id = None
	for index in latest_files_indexes:
		if index['gameVersion'] == game_version:
			return index['fileId']
	if file_id is None:
		print('Warning! No files found for ' + game_version + ' (1)!')
		return None

def get_file_json(modid, file_id):
	url = api_base_url + '/mods/' + str(modid) + '/files/' + str(file_id)
	response = requests.get(url)
	if response is None or response.status_code != 200:
		return None
	return response.json()

def get_file_url_from_json(json_):
	file_id = get_file_id_from_json(json_)
	if file_id is None:
		return None
	file_json = get_file_json(str(json_['data']['id']), file_id)
	if file_json is None:
		return None
	return file_json['data']['downloadUrl']

def write_JSON(data, json_file):
	with open(json_file, 'w') as json_file_:
		pp = pprint.PrettyPrinter(indent=4)
		json_file_.seek(0)
		json.dump(data, json_file_, indent=4)
		json_file_.truncate()

def get_last_page_from_progress_file():
	if not os.path.exists(progress_file):
		return None
	with open(progress_file, 'r+') as file:
		lines = file.readlines()
		lines = [line.rstrip() for line in lines]
		i = len(lines) - 1
		while (i >= 0):
			if lines[i].startswith('page'):
				return lines[i][5:]
		return None

def yes_or_no(question):
	while "invalid option":
		reply = str(input(question+' (y/n) (default: y): ')).lower().strip()
		if len(reply) == 0:
			return True
		if reply[0] == 'y':
			return True
		if reply[0] == 'n':
			return False

def get_amount_of_pages():
	page = scraper.get(base_url)
	if page is None or page.status_code != 200 or page.content is None:
		die("Couldn't get the amount of pages (1)")
	soup = BeautifulSoup(page.content, 'html.parser')
	target_divs = soup.find_all('div', {'class': 'pagination pagination-top flex items-center'})
	if len(target_divs) == 0:
		die("Couldn't get the amount of pages (2)")
	page_links = target_divs[0].findChildren('a', {'class': 'pagination-item'})
	if len(page_links) == 0:
		die("Couldn't get the amount of pages (3)")
	return page_links[len(page_links) - 1].text

def get_ids_for_page(page):
	page = scraper.get(base_url + '&page=' + page)
	if page is None or page.status_code != 200 or page.content is None:
		die("Couldn't get page " + page)
	soup = BeautifulSoup(page.content, 'html.parser')
	links = soup.find_all('a', {'class': 'my-auto'})
	if len(links) == 0:
		die("Couldn't get mod links")
	mod_links = []
	for elem in links:
		if not 'minecraft/mc-mods' in elem['href']:
			continue
		mod_links.append(elem)
	res = []
	for link in mod_links:
		res.append(get_mod_id_by_url('https://www.curseforge.com' + link['href']))
	return res

def get_mod_id_by_url(url):
	print('Getting mod id, url: ' + url)
	page = scraper.get(url)
	if page is None or page.status_code != 200 or page.content is None:
		die("Couldn't get mod page " + url)
	soup = BeautifulSoup(page.content, 'html.parser')
	divs = soup.find_all('div', {'class': 'w-full flex justify-between'})
	if len(divs) == 0:
		die("Couldn't get mod id")
	text = divs[0].text
	return text[12:len(text) - 1]

def save_mod_page_progress(page):
	if os.path.exists(progress_file):
		with open(progress_file, 'r+') as file:
			lines = file.readlines()
			lines = [line.rstrip() for line in lines]
			#print(lines)
			if 'page ' + str(page) not in lines:
				lines.append('page ' + str(page))
				file.seek(0)
				file.write('\n'.join(lines) + '\n')
				file.truncate()
	else:
		with open(progress_file, 'w') as file:
			file.write('page ' + str(page) + '\n')


def die(msg):
	sys.exit(msg)

if __name__ == '__main__':
	main()