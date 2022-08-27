#!/usr/bin/python3

import argparse
import os
import threading

import requests

downloaded = 0

def main():
	global downloaded

	parser = argparse.ArgumentParser(description='CurseForge Minecraft 1.7.10 mod scraper.')
	
	parser.add_argument('-v', '--version', type=str, help="Minecraft version. Default: 1.7.10.")
	parser.add_argument('-d', '--downloads', type=str, help="Location of downloaded files. Default: downloads.")
	parser.add_argument('-t', '--threads', type=str, help="Amount of download threads. Default: 4.")
	parser.add_argument('-u', '--useragent', type=str, help="User agent.")
	parser.add_argument('-f', '--uafrom', type=str, help="Name of the program creator/user.")

	args = parser.parse_args()
	
	mc_version = '1.7.10'
	download_location = 'downloads'
	threads = 4
	useragent = 'Modrinth archiver 9000'
	from_ = 'Sneedster69'

	if args.version:
		mc_version = args.version
	if args.downloads:
		download_location = args.args.downloads
	if args.threads:
		threads = int(args.threads)
	if args.useragent:
		useragent = args.useragent
	if args.uafrom:
		from_ = args.uafrom

	headers = {
		'User-Agent': useragent,
		'From': from_
	}

	url = 'https://api.modrinth.com/v2/search?offset={OFFSET}&limit={LIMIT}&index=newest&facets=[[%22versions:' + mc_version + '%22],["project_type:mod"]]'
	project_url = 'https://api.modrinth.com/v2/project/{PROJECT_ID}'
	version_url = 'https://api.modrinth.com/v2/version/{VERSION_ID}'

	resp = requests.get(url.replace('{OFFSET}', '0').replace('{LIMIT}', '1'), headers=headers)
	if resp.status_code != 200:
		die('Failed to connect')
	hit_amount = int(resp.json()['total_hits'])
	
	mod_urls = []

	step = 50

	i = 0
	while(i * step < hit_amount):
		print('fetching mods (' + str(i) + ')')
		resp = requests.get(url.replace('{OFFSET}', str(i * step)).replace('{LIMIT}', str(step)), headers=headers)
		if resp.status_code != 200:
			die('Failed to connect')
		mod_ids = []
		for hit in resp.json()['hits']:
			#print('appending ' + hit['project_id'])
			mod_ids.append(hit['project_id'])
		for mod_id in mod_ids:
			resp = requests.get(project_url.replace('{PROJECT_ID}', mod_id), headers=headers)
			if resp.status_code != 200:
				continue
			versions = resp.json()['versions']
			intredasting_version = versions[len(versions) - 1]
			resp = requests.get(version_url.replace('{VERSION_ID}', intredasting_version), headers=headers)
			if resp.status_code != 200:
				continue
			for file in resp.json()['files']:
				mod_urls.append(file['url'])
		i += 1

	download_lists = split(mod_urls, threads)

	if not os.path.exists(download_location):
		os.makedirs(download_location)
	
	for elem in download_lists:
		download_thread = threading.Thread(target=download_list, args=(elem,len(mod_urls),download_location,headers))
		download_thread.start()

def get_filename_from_url(url):
	return url[url.rfind('/') + 1:]

def download_list(list_, total, download_location, headers):
	global downloaded

	for elem in list_:
		filepath = os.path.join(download_location, get_filename_from_url(elem))
		print('Downloading ' + get_filename_from_url(elem))
		if os.path.exists(filepath):
			print('File already exists')
		else:
			r = requests.get(elem, allow_redirects=True, headers=headers)
			open(filepath, 'wb').write(r.content)
			downloaded += 1
			print('Downloaded ' + str(downloaded) + ' files out of ' + str(total))

def split(a, n):
	k, m = divmod(len(a), n)
	return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def die(msg):
	sys.exit(msg)

if __name__ == '__main__':
	main()