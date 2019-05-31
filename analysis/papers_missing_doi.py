# papers_missing_doi.py
# prints model_ids with papers with no doi.

from urllib2 import urlopen
import urllib2
from bs4 import BeautifulSoup, Comment

# get list of all models
all_models = []
all_models_html = urlopen('https://senselab.med.yale.edu/ModelDB/ListByModelName.asp?c=19&lin=-1').read()
all_models_soup = BeautifulSoup(all_models_html, 'html5lib')
print "Retrieving model ids"
for link in all_models_soup.find_all('a'):
    href = link.get('href')
    if href is not None and 'ShowModel.asp?model=' in href:
        model_id = int(href.split('=')[1])
        all_models.append(model_id)

all_models.sort()

print all_models

# this dict will hold whether (doi) or not (None) a model_id has a paper with a doi
model_id_doi = {}
print "finding doi's or not:"
# load the modeldb entry
href_list=[]
cntr=0
for model_id in all_models:
  model_html = urlopen('http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=%d' % model_id).read()
  model_soup = BeautifulSoup(model_html, 'html5lib')
  paper_doi = None
  for link in model_soup.find_all('a'):
    href = link.get('href')
    href_list.append(href)
    if href is not None and 'http://dx.doi.org/' == href[ : 18]:
        paper_doi = href[18 :]
        print "*** found a doi: "+paper_doi
    cntr = cntr + 1
    model_id_doi[model_id]=paper_doi

print "model_id: doi"
for model_id in all_models:
  print repr(model_id)+": "+repr(model_id_doi[model_id])
