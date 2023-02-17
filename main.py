import requests
from bs4 import BeautifulSoup
from more_itertools import intersperse
from tqdm import tqdm
import csv

decluttr_iphone = 'https://www.decluttr.com/sell-my-cell-phone/sell-my-iphone/'
decluttr_url = 'https://www.decluttr.com'
product_url = 'https://www.decluttr.com/product-details?barcode=i'
gen = '&gen='
url_separator = '%20'
brand = 'Apple'
ebay_url = f'https://www.ebay.com/sch/i.html?_from=R40&_nkw=phones&_sacat=3&rt=nc&Brand={brand}&_dcat=9355&_pgn='

class PurchaseProposal:
  def __init__(self, gen, price, url, capacity):
     self.gen = gen
     self.price = price
     self.url = url
     self.capacity = capacity
     
  def __str__(self):
    return ' '.join(self.gen) + ' ' +  self.capacity + ' ' + self.price + ' ' + self.url
  
class EbayOffer:
  def __init__(self, title, price, url):
    self.title = title
    self.price = price
    self.url = url
    self.capacity_match = False
    self.proposal = None
    
  def add_proposal(self, proposal):
    self.proposal = proposal
    if proposal.capacity in self.title:
      self.capacity_match = True
    
  def __str__(self):
    return self.title +  ' ' + self.price + ' ' + self.url + '\n' + str(self.proposal)



def get_urls():
  res_decluttr = requests.get(decluttr_iphone)
  decluttr_soup = BeautifulSoup(res_decluttr.text, 'html.parser')

  iphone_buttons = decluttr_soup.find_all(string = 'Sell Now')
  urls = [decluttr_url + url.parent['href'].replace(' ', '%20') for url in iphone_buttons]
  return urls

def get_gen_pages(urls):
  return [BeautifulSoup(requests.get(url).text, 'html.parser') for url in tqdm(urls)]

def get_gen_iphones(gen_pages, urls):
  products_infos = [list(x.find('h1', class_ = 'desktop-header').children) for x in gen_pages]
  full_titles = [(children[0]) for children in products_infos]
  prices = [''.join([x for x in children[1].string if x.isdigit() or x == '.']) for children in products_infos]

  title_split = [full_title.split(' ') for full_title in full_titles]
  capacity = []
  for title in title_split:
    title.pop()
    title.pop(0)
    capacity.append(title.pop())

  iphones = []
  for i in range(len(title_split)):
    iphones.append(PurchaseProposal(title_split[i], prices[i], urls[i], capacity[i]))
  return iphones, title_split


def is_barcode(barcode):
  return 'i00000' in barcode




def get_capacity_urls(gen_pages, urls):
  capacity_urls = []
  for i in range(len(gen_pages)):
    scripts = gen_pages[i].find_all('script')
    for script in scripts:
      if 'techSizes' in str(script.string):
        sizes = [line for line in str(script.string).split('\n') if 'techSizes' in line][0]
        str_dict = sizes[sizes.find('['):len(sizes) - 1]
        json_split = str_dict.split(' ')
        raw_barcodes = list(filter(is_barcode, json_split))
        barcodes = [(''.join([x for x in barcode if x.isdigit()])) for barcode in raw_barcodes]
        for barcode in barcodes: 
          new_url = product_url + barcode + gen + ''.join(list(intersperse(url_separator, iphones[i].gen)))
          if new_url not in urls:
            capacity_urls.append(new_url)
  return capacity_urls

def get_capacity_pages(capacity_urls):
  return [BeautifulSoup(requests.get(url).text, 'html.parser') for url in tqdm(capacity_urls)]


def get_product_infos(capacity_pages):
  try:
    return [list(x.find('h1', class_ = 'desktop-header').children) for x in capacity_pages]
  except:
    print('FAILED TO FETCH A PRODUCT DATA -- EXITING')
    exit()

def get_titles(product_infos):
  full_titles = [(children[0]) for children in product_infos]
  return [full_title.split(' ') for full_title in full_titles]

def get_prices(product_infos):
 return [''.join([x for x in children[1].string if x.isdigit() or x == '.']) for children in product_infos]

def get_capacity(titles):
  capacity = []
  for title in titles:
    title.pop()
    title.pop(0)
    capacity.append(title.pop())
  return capacity

def save_data(iphones, output_file = './decluttr.txt'):
  output = open(output_file, 'w')
  for iphone in iphones:
    output.write(str(iphone))
    output.write('\n')
    
def read_data(input_file):
  lines = open(input_file, 'r' )
  iphones = []
  for line in lines:
    split =  line.split()
    capacity_pos = split.index(next(word for word in split if 'B' in word or 'b' in word))
    iphones.append(PurchaseProposal(split[:capacity_pos], split[capacity_pos + 1], split[capacity_pos + 2], split[capacity_pos]))
  return iphones
  
def fetch_ebay(page):
  url = ebay_url + str(page)
  res_ebay = requests.get(url)
  ebay_soup = BeautifulSoup(res_ebay.text, 'html.parser')
  items = ebay_soup.find_all(class_ = 's-item__info')
  ebay_offers = []
  print(f'----- Fetching {len(items)} ebay offers -----')
  for item in tqdm(items):
    price = item.find(class_ = 's-item__price')
    title = item.find(class_ = 's-item__title')
    url = item.find(class_ = 's-item__link')
    if title.string and price.contents[0].string and url['href']:
      ebay_offers.append(EbayOffer(title.string, price.contents[0].string, url['href']))
  return ebay_offers
  
def fetch_data():
  urls = get_urls()
  print('----- Generating the gen pages ------')
  gen_pages = get_gen_pages(urls)
  print(f'----- Found {len(gen_pages)} generations -----')
  iphones, title_split = get_gen_iphones(gen_pages, urls)
  capacity_urls = get_capacity_urls(gen_pages, urls)
  print('----- Generating the capacity pages ------')
  capacity_pages = get_capacity_pages(capacity_urls)
  print(f'----- Found {len(capacity_pages)} capacity -----')
  product_infos = get_product_infos(capacity_pages)
  titles = get_titles(product_infos)
  prices = get_prices(product_infos)
  capacity = get_capacity(titles)
  for i in range(len(titles)):
    iphones.append(PurchaseProposal(titles[i], prices[i], capacity_urls[i], capacity[i]))   
  return iphones

def write_csv(offers, output = './offers.csv'):
  new_csv = open(output, 'w', newline = '')
  csv_writer = csv.writer(new_csv)
  for offer in offers:
    csv_writer.writerow([offer.url, offer.proposal.url, float(''.join([x for x in offer.proposal.price if x.isdigit() or x=='.'])) - float(''.join([x for x in offer.price if x.isdigit() or x=='.']))])
  
if __name__ == '__main__':
  iphones = read_data('./decluttr.txt')
  ebay_offers = fetch_ebay(1)
  print(len(ebay_offers))
  ebay_offers_2 = fetch_ebay(2)
  ebay_offers_3 = fetch_ebay(3)
  ebay_offers = ebay_offers + ebay_offers_2 + ebay_offers_3
  print(len(ebay_offers))
  matching_offers = []
  for ebay_offer in ebay_offers:
    for iphone in iphones:
      if all(name in ebay_offer.title.split(' ') for name in iphone.gen):
        if float(''.join([x for x in iphone.price if x.isdigit() or x=='.'])) - float(''.join([x for x in ebay_offer.price if x.isdigit() or x=='.'])) > 0:
          ebay_offer.add_proposal(iphone)
    if ebay_offer.proposal:    
      matching_offers.append(ebay_offer)
  write_csv(matching_offers)
        
  
  