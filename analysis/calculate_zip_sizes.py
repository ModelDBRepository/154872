from urllib2 import urlopen
import urllib2
from bs4 import BeautifulSoup
import cPickle
from matplotlib import pyplot

# get list of neuron models
neuron_models = []
neuron_models_html = urlopen('http://senselab.med.yale.edu/modeldb/ListByModelName.asp?c=19&lin=-1').read()
neuron_models_soup = BeautifulSoup(neuron_models_html, 'html5lib')
for link in neuron_models_soup.find_all('a'):
    href = link.get('href')
    if href is not None and 'ShowModel.asp?model=' in href:
        model_id = int(href.split('=')[1])
        neuron_models.append(model_id)

neuron_models.sort()

zip_lengths = {}
no_zip = []

def analyze_zip(model_id):
    try:
        zipfile = urlopen('http://senselab.med.yale.edu/modeldb/eavBinDown.asp?o=%d&a=23&mime=application/zip' % model_id).read()
        zip_lengths[model_id] = len(zipfile)
    except urllib2.HTTPError:
        no_zip.append(model_id)
        return False
    return True

for model in neuron_models:
    analyze_zip(model)

with open('zip_lengths.txt', 'w') as f:
    f.write(cPickle.dumps({'zip_lengths': zip_lengths, 'no_zip': no_zip}))

pyplot.hist(zip_lengths.values(), 50)
pyplot.xlabel('Zip length (bytes)')
pyplot.ylabel('Count')
pyplot.title('%d dropped because no zip' % len(no_zip))
pyplot.show()
