import rdflib
import urllib
import time

scholars_base = "http://demo.scholars.cornell.edu/scholars/"
vivo_base = "http://vivo.cornell.edu/"
listrdf = 'listrdf?vclass='
reconcile = 'reconcile'


def getInstances(instanceURI):
    vivo_instances = rdflib.Graph()
    queryurl = vivo_base + listrdf + urllib.parse.quote(instanceURI,
                                                            safe='')
    vivo_instances.parse(queryurl)
    for name in vivo_instances.subjects(None, rdflib.term.URIRef(instanceURI)):
        vivo_instances.parse(name)
        time.sleep(1):
    return(vivo_instances)


def getRelatedTo(relatedDept, instances):



if __name__ == '__main__':
    main()

