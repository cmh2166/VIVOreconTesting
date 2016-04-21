"""Match people from VIVO department to eCommons roles."""
import rdflib
from rdflib.namespace import RDF, FOAF
import xmltodict
import csv
import json
import sys
import ecommonsharvest
from fuzzywuzzy import fuzz
import os.path, time
"""
Values-matching, if > 85:
generate eCommons update with URIs
generate VIVO updates with handles, role

Validate matches = specializations?
"""
VIVO = rdflib.Namespace("http://vivoweb.org/ontology/core#")
hr = rdflib.Namespace("http://vivo.cornell.edu/ns/hr/0.9/hr.owl#")
ns = {'http://www.openarchives.org/OAI/2.0/': None,
      'http://www.dspace.org/xmlns/dspace/dim': 'dim'}
roles = ['chair', 'committeeMember', 'coChair', 'advisor']


def getVIVOppl(deptURI):
    """Generate VIVO Graph containing people in that dept, return people."""
    VIVOgraph = rdflib.Graph()
    print("Getting VIVO department data...")
    try:
        if type(deptURI) is str:
            VIVOgraph.parse(deptURI)
        elif type(deptURI) is list:
            for URI in deptURI:
                VIVOgraph.parse(URI)
    except Exception as e:
        print("Error parsing VIVO URIS: %s" % e)
        exit()

    print("Getting VIVO units data...")
    for unit in VIVOgraph.objects(None, VIVO.relatedBy):
        VIVOgraph.parse(unit)
    print("Getting VIVO positions data...")
    for pos in VIVOgraph.subjects(hr.positionInUnit, None):
        VIVOgraph.parse(pos)
    people = {}
    print("Getting VIVO people data...")
    for person in VIVOgraph.subjects(RDF.type, FOAF.Person):
        # do further testing to ensure we grab only employees
        label = VIVOgraph.preferredLabel(person)[0][1].toPython()
        people[person.toPython()] = label
    print("got VIVO graph successfully.")
    with open("data/VIVOnames.json", 'w') as f:
        json.dump(people, f)
    return(people)


def retrieveECommons():
    """grab eCommons data if not existant/too old."""
    print("Testing last retrieval date of eCommons.")
    lastECgrabdate = os.path.getmtime('data/eCommons.xml')
    if time.time() - lastECgrabdate > (3 * 30 * 24 * 60 * 60):
        print("Too old. Grabbing new eCommons dataset.")
        ecommonsharvest.main()
    else:
        print("Using current set stored locally.")


def eCommonsXMLtoDict(eCommonsXML):
    """Translate eCommons XML to dict."""
    with open(eCommonsXML) as fd:
        eCommonsDict = xmltodict.parse(fd.read(), namespaces=ns)
    return(eCommonsDict)


def eCommonsRoles(eCommonsDict):
    """Grab eCommons records only with wanted roles."""
    eCommonsSubset = {}
    print("Getting only eCommons records with chosen roles.")
    for n in range(len(eCommonsDict['OAI-PMH']['ListRecords']['record'])):
        try:
            metadata = eCommonsDict['OAI-PMH']['ListRecords']['record'][n]['metadata']
        except KeyError:
            pass
        for m in range(len(metadata['dim:dim']['dim:field'])):
            field = metadata['dim:dim']['dim:field'][m]
            try:
                if field['@element'] == 'contributor' and field['@qualifier'] in roles:
                    eCommonsSubset['record'] = eCommonsDict['OAI-PMH']['ListRecords']['record'][n]
                    pass
                else:
                    pass
            except KeyError:
                pass
    print("Saving eCommons roles locally as a backup.")
    with open("data/eCommonsRoles.json", 'w') as f:
        json.dump(eCommonsSubset, f)
    return(eCommonsSubset)


def compareECtoVIVO(VIVOppl, eCommonsDict):
    """compare eCommons to VIVO."""
    print('Now matching VIVO to eCommons')
    VIVOmatches = {}
    eCommonsMatched = {}
    for n in range(len(eCommonsDict['record'])):
        record = ['record'][n]
        metadata = record['metadata']
        for m in range(len(metadata['dim:dim']['dim:field'])):
            field = metadata['dim:dim']['dim:field'][m]
            if field['@element'] == 'identifier' and field['@qualifier'] == 'uri':
                handle = field['#text']
        for m in range(len(metadata['dim:dim']['dim:field'])):
            field = metadata['dim:dim']['dim:field'][m]
            if field['@element'] == 'contributor' and field['@qualifier'] in roles:
                for uri, label in VIVOppl.items():
                    matchranking = fuzz.ratio(label, field['#text'])
                    print("Matching: " + label + " to " + field['#text'] +
                          " with score: " + str(matchranking))
                    if matchranking > 90:
                        VIVOmatches[label] = {}
                        VIVOmatches[label]['uri'] = uri
                        VIVOmatches[label]['label'] = label
                        VIVOmatches[label]['handle'] = handle
                        VIVOmatches[label]['role'] = field['@qualifier']
                        VIVOmatches[label]['eCommonsLabel'] = field['#text']
                        eCommonsMatched[handle] = record
                        vivoaddition = {}
                        vivoaddition['@element'] = 'contributor'
                        vivoaddition['@qualified'] = field['@qualifier'] + "_uri"
                        vivoaddition['#text'] = uri
                        eCommonsMatched[handle]['metadata']['dim:dim']['dim:field'] = vivoaddition
    return(VIVOmatches, eCommonsMatched)


def writeVIVOtoCsv(dictionary):
    """Write the matching outputs to CSV for reingest."""
    with open('data/VIVOmatched.csv', 'w') as f:
        w = csv.DictWriter(f, dictionary.keys())
        w.writerow(dictionary)


def writeECtoCsv(dictionary):
    """Write the matching outputs to JSON for now. To be fixed."""
    with open('data/ECmatched.json') as f:
        json.dump(dictionary, f)


def main():
    """Main function: run people matching."""
    try:
        deptURI = sys.argv[1]
    except IndexError:
        print("Please provide a URI or list of URIs")
        exit()
    if type(deptURI) is str or type(deptURI) is list:
        # grab VIVO data
        VIVOppl = getVIVOppl(deptURI)
        # grab eCommons data
        retrieveECommons()
        eCommonsAll = eCommonsXMLtoDict("data/eCommons.xml")
        # only review records that have roles to be queried
        eCommonsSubset = eCommonsRoles(eCommonsAll)
        # compare eCommonsSubset with VIVO names
        VIVOmatched, eCommonsMatched = compareECtoVIVO(VIVOppl, eCommonsSubset)
        # write updates to csv for reingest
        writeVIVOtoCsv(VIVOmatched)
        writeECtoCsv(eCommonsMatched)
    else:
        print("Please provide a URI or list of URIs")
        exit()


if __name__ == "__main__":
    main()
