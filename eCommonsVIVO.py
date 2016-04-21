import rdflib
from rdflib.namespace import RDF, FOAF
import xmltodict
import csv
import sys
import os
"""
VIVO: grab college of engineering URI(s)
Create rdflib.Graph()
iterate through relatedby/relates, positionInUnit
grab all instances of FOAF:Agent
create matching dict: uri: label (pref + alt?)

eCommons:
oai:feed, grab DIM
dc.contributor.[advisor|chair|coChair|committeeMember]
create dict: hdl : label

Values-matching, if > 85:
generate eCommons update with URIs
generate VIVO updates with handles, role

Validate matches = specializations?
"""
VIVO = rdflib.Namespace("http://vivoweb.org/ontology/core#")
hr = rdflib.Namespace("http://vivo.cornell.edu/ns/hr/0.9/hr.owl#")


def getVIVOppl(deptURI):
    VIVOgraph = rdflib.Graph()
    try:
        if type(deptURI) is str:
            VIVOgraph.parse(deptURI)
        elif type(deptURI) is list:
            for URI in deptURI:
                VIVOgraph.parse(URI)
    except Exception as e:
        print("Error parsing VIVO URIS: %s" % e)
        exit()

    for unit in VIVOgraph.objects(None, VIVO.relatedBy):
        VIVOgraph.parse(unit)
    for pos in VIVOgraph.subjects(hr.positionInUnit, None):
        VIVOgraph.parse(pos)
    people = {}
    for person in VIVOgraph.subjects(RDF.type, FOAF.Person):
        # do further testing to ensure we grab only employees
        label = VIVOgraph.preferredLabel(person)[0][1].toPython()
        people[person.toPython()] = label
    return(people)


def getEcommonsPpl():
    if not os.path.exists('data'):
        os.makedirs('data')


def main():
    try:
        deptURI = sys.argv[1]
    except IndexError:
        print("Please provide a URI or list of URIs")
        exit()
    if type(deptURI) is str or type(deptURI) is list:
        # grab VIVO data
        VIVOppl = getVIVOppl(deptURI)
        # grab eCommons data
        print(VIVOppl)

    else:
        print("Please provide a URI or list of URIs")
        exit()


if __name__ == "__main__":
    main()
