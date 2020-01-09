import sys
import os
import re
import shutil
import requests
import time
import logging
import argparse
#import winsound
from tqdm import tqdm
from bs4 import BeautifulSoup
from datetime import datetime
Options = None

# OK - Tested
def reset_options():
	for arg in vars(Options): 
		if type(getattr(Options, arg)) is bool:
			setattr(Options, arg, False)
		else:
			setattr(Options, arg, None)

# OK - Tested
def get_folder_info():

	if Options.folder is not None:
		folder_path = Options.folder[0]
	else:
		if Options.pool is not None:  		folder_path = Options.pool[0]
		elif Options.tags is not None: 		folder_path = Options.tags[0]
		elif Options.single is not None:	folder_path = "Single Posts"

	if not Options.unsafe:
		folder_path = re.sub(r'[\\/*?:"<>|]', '', folder_path)
	
	folder_path = Options.type[0] + '\\' + folder_path
	os.makedirs(folder_path, exist_ok=True)
	return folder_path, [file.split(' ')[0] for file in os.listdir(folder_path)]

# OK - Tested
def download_singles():

	start_time = datetime.now()

	logging.info("\tDOWNLOAD MODE : SINGLE POSTS")
	folder, folder_files = get_folder_info()
	posts_checked = 0
	posts_downloaded = 0

	#for post_ID in Options.single:
	for post_ID in (Options.single if not Options.hide else tqdm(Options.single, desc='Downloading')):
		posts_checked += 1
		posts_downloaded += process_post(post_ID, folder, folder_files)
	
	logging.info("\n")

	logging.info("\tNº OF POSTS CHECKED: {}".format(posts_checked))
	logging.info("\tNº OF POSTS DOWNLOADED: {}".format(posts_downloaded))
	logging.info("\tSTART DATE : {}".format(start_time.strftime('%x %X')))
	logging.info("\tEND DATE : {}".format(datetime.now().strftime('%x %X')))
	logging.info("\tTIME ELAPSED : {}".format(str(datetime.now() - start_time).split('.', 2)[0]))

# OK - Tested
def download_using_pages(mode):

	download_start = time.time()
	start_time = time.strftime("%x %X", time.localtime())
	folder, folder_files = get_folder_info()

	if mode == 'pool':
		logging.info("\tDOWNLOAD MODE : POOL")
		logging.info("\tPOOL ID : {}".format(Options.pool[0]))
	else:
		logging.info("\tDOWNLOAD MODE : TAG SEARCH")
		logging.info("\tTAG LIST : {}\n".format(Options.tags[0]))

	logging.info("\t.START\n")

	page_num = int(Options.start[0]) if Options.start is not None else 1
	posts_checked = 0
	posts_downloaded = 0

	while True:

		if Options.end is not None:
			if page_num > int(Options.end[0]):
				break

		posts = fetch_posts(page_num)	# Fetch Posts' IDs
		
		# No More Posts ==> End Of Pool
		if len(posts) == 0:	break
		time.sleep(Options.time[0] if Options.time is not None else 5)

		print('Page: ', page_num) if not Options.hide else None
		for post_ID in (posts if not Options.hide else tqdm(posts, desc='Page {}'.format(page_num))):
			posts_checked += 1
			posts_downloaded += process_post(post_ID, folder, folder_files)

		page_num += 1

	logging.info("\t.END\n")

	logging.info("\tNº OF POSTS CHECKED: {}".format(posts_checked))
	logging.info("\tNº OF POSTS DOWNLOADED: {}".format(posts_downloaded))
	logging.info("\tSTART DATE : {}".format(start_time))
	logging.info("\tEND DATE : {}".format(time.strftime("%x %X", time.localtime())))
	logging.info("\tTIME ELAPSED : {}".format(time.strftime("%X", time.gmtime(time.time() - download_start))))

# OK - Tested
def fetch_posts(page_num):
	if Options.pool is not None:
		response = requests.get('https://{}.sankakucomplex.com/pool/show/{}?page={}'.format(Options.type[0], Options.pool[0], page_num))
	elif Options.tags is not None:
		response = requests.get('https://{}.sankakucomplex.com/?tags={}&page={}'.format(Options.type[0], '+'.join(Options.tags[0].split(',')), page_num))
	else:
		return []

	soup = BeautifulSoup(response.text, "html.parser")
	return [link.get('href').split('/')[-1] for link in soup.findAll('a') if '/post/show/' in link.get('href')]

# OK - Tested
def process_post(post_ID, folder_path, folder_files):

	if post_ID not in folder_files:

		response = requests.get("https://{}.sankakucomplex.com/post/show/{}".format(Options.type[0], post_ID))
		soup = BeautifulSoup(response.text, "html.parser")
		time.sleep(Options.time[0] if Options.time is not None else 5)

		for link in soup.find_all('a'):
			if '.sankakucomplex.com/data' in link.get('href') and 'sample' not in link.get('href'):
				
				media_url = 'http://' + link.get('href')[2:]
				
				# Get the rating (Safe | Questionable | Explicit)
				for list_item in soup.findAll('li'):
					if "Rating:" in str(list_item.contents[0]):
						post_rating = " " + str(list_item.contents[0]).split(':')[-1].strip()

				post_tags = [tag.strip() for tag in re.sub(r'[\\/*?:"<>|]', '', soup.title.string).split('Sankaku Channel')[0].split(',')]

				# We use the post id and tags to build a filename
				filename = post_ID

				for tag in post_tags:
					if len(os.getcwd() + "\\" + folder_path + "\\" + filename + " " + tag + post_rating) > 256:
						break
					else: 
						filename += " " + tag

				filename += post_rating
				filename += '.' +  media_url.split('?')[0].split('.')[-1]

				save_file(folder_path, filename, media_url, soup)
				folder_files.append(post_ID)
				return 1
	else:

		if not Options.hide: 
			print("Duplicate -> Post with ID", post_ID, "has already been saved to", folder_path)

		logging.info('\tPost already saved in "{}"\t -> {}'.format(folder_path, post_ID))
		return 0

# OK - Tested
def save_file(folder, filename, file_url, soup):
	data = requests.get(file_url, stream=True) 
	data.raw.decode_content = True

	with open(folder + '\\' + filename, "wb" ) as f:	
		shutil.copyfileobj(data.raw, f)

	with open('download_log.txt', 'a+') as f:
		f.write('{} -- Post with ID {} saved into "{}"\n'.format(time.strftime("%x %X", time.localtime()), filename.split(' ')[0], os.path.normpath(folder)))

	logging.info('\tPOST ID : {}'.format(filename.split(' ')[0]))
	logging.info('\tRATING : {}'.format(filename.split('.')[-2].split(' ')[-1]))
	logging.info('\tARTIST(S) : {}'.format([tag.contents[0].contents[0] for tag in soup.findAll('li', class_='tag-type-artist')]))
	logging.info('\tCOPYRIGHT(S) : {}'.format([tag.contents[0].contents[0] for tag in soup.findAll('li', class_='tag-type-copyright')]))
	logging.info('\tSTUDIO/CIRCLE : {}'.format([tag.contents[0].contents[0] for tag in soup.findAll('li', class_='tag-type-studio')]))
	logging.info('\tPOOL(S) : {}'.format([pool.get('href').strip().split("/")[-1] for pool in soup.find_all(href=re.compile("/pool/show/"))]))
	logging.info('\tCHARACTER(S) : {}'.format([tag.contents[0].contents[0] for tag in soup.findAll('li', class_='tag-type-character')]))

	other_tags = []
	for tag in soup.findAll('li', {'class':['tag-type-medium', 'tag-type-general', 'tag-type-meta']}):
		other_tags.append(tag.contents[0].contents[0])
		
	logging.info('\tOTHER TAGS : {}\n'.format(other_tags))

	if not Options.hide: 
		if len(filename) >= 80: filename = ''.join(filename[:80]) + "..."
		print('Downloaded: ', filename, 'into', os.path.normpath(folder))

	time.sleep(Options.time[0] if Options.time is not None else 5)

# Needs proper testing
def main():

	print()

	log_folder = "Logs"
	os.makedirs(log_folder, exist_ok=True)
	arguments = []

	for i, arg in enumerate(vars(Options)):
		value = getattr(Options, arg)
		if value not in (False, None):
			if type(value) == list:
				arguments.append("{}{}".format(arg, value))
			else:
				arguments.append("{}({})".format(arg, value))

	with open('download_log.txt', 'a+') as f: 
		f.write('\nArguments: {}\n'.format(str(arguments).replace("'", "").replace('"', "")))

	
	log_file_name = str(time.strftime("%Y-%m-%d -- %H.%M.%S", time.localtime())) + ' '
	log_file_name += re.sub(r'[\\/*?:"<>|]', '', " ".join(arguments))
	log_file_name = log_file_name.replace("'", "")

	path_length = len(os.getcwd() + '\\' + log_folder + '\\' + log_file_name + '.txt')
	if path_length > 256:
		overflow = path_length - 256
		log_file_name = log_file_name[:-overflow]

	log_file_name += '.txt'

	logging.basicConfig(handlers=[logging.FileHandler(log_folder + '\\' + log_file_name, 'w', 'utf-8')],level=logging.INFO)
	logging.info(" -- SANKAKU SCRAPPER -- \n")
	logging.info(" ## ARGUMENT LIST ## ")
	for i, arg in enumerate(vars(Options)):
		message = "\t{} : {}".format(arg.upper(), getattr(Options, arg))
		logging.info(message + '\n') if i == len(vars(Options))-1 else logging.info(message)

	if Options.queue is not None:

		cnt = 1
		logging.info("\tDOWNLOAD MODE : QUERY\n")
		with open(Options.queue[0], 'r') as f:
			for line in f:

				if line[0] == '#' or line.strip() == '':
					print(line.strip())
				elif line[0] == '@':
					break
				else:
					print("## Query Nº {} ##".format(cnt))
					logging.info("\tArgument list Nº {}: {}".format(cnt, line.strip()))

					opt_list = [x for x in line.strip().split()]
					for opt in opt_list:
						key,value = opt.split(':', maxsplit=1)
						setattr(Options, key, [value])

					if Options.pool is not None: 		download_using_pages('pool')
					elif Options.tags is not None: 		download_using_pages('tags')
					elif Options.single is not None:	download_singles()

					reset_options()
					print('\n\n')
					cnt += 1

	elif Options.pool is not None: 		download_using_pages('pool')
	elif Options.tags is not None: 		download_using_pages('tags')
	elif Options.single is not None:	download_singles()
	else:
		parser.print_help()

if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	# Obligatory Options
	parser.add_argument('--type', help="You can choose between 'chan' for chan.sankakucomplex or 'idol' for idol.sankakucomplex", type=str, metavar=("SANKAKU_TYPE"), nargs=1, default="chan")

	# Download Options
	parser.add_argument('--tags', help="Given one or more tags, separated by commas, the script will try to download posts that match those tags.", nargs='+', metavar=('T'))
	parser.add_argument('--pool', help="Downloads an entire pool. Can be used along with --start and --end.", nargs=1,metavar=('POOL_ID'))
	parser.add_argument('--single', help="Given one or more posts' ids, the script will download the posts into the 'Single Posts' folder or folder of your choice.", nargs="+",metavar=('ID'))
	parser.add_argument('--queue', help="It will read the text file and treat each line as arguments.", type=str, metavar=('TEXT_FILE'), nargs=1)

	# Optional
	parser.add_argument('--start', help="Selects at what page should the download start.", type=int, nargs=1,metavar=('PAGE_NUM'))
	parser.add_argument('--end', help="Selects at what page should the download end.", type=int, nargs=1,metavar=('PAGE_NUM'))

	parser.add_argument('--time', help="Changes the delay between requests. The default value is 5. Going any lower may result in you getting blocked or blacklisted from any Sankaku site.", type=int, nargs=1, metavar=('SECONDS'))
	parser.add_argument('--folder', help="Given a valid folder path, the script will save all files into the provided folder, as long as it exists.",type=str, metavar=('FOLDER'), nargs=1)
	parser.add_argument('--unsafe', help='If enabled, it lets you choose a folder name that includes special characters, like slashes (/) or two dots (..) e.g., ../touhou/alice_margatroid', action='store_true')
	parser.add_argument('--hide', help='The script displays a progress bar instead of printing a line per post downloaded.', action='store_true')
	#parser.add_argument('--dups', help='If present, the script will halt once it finds N duplicate files.',type=int, nargs=1,metavar=('N'))
	#parser.add_argument('--check', help="", action="store_true")

	Options = None
	Options = parser.parse_args()
	main()
