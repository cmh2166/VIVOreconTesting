"""Match people from VIVO department to eCommons roles."""
import rdflib
from rdflib.namespace import RDF, FOAF
import xmltodict
import csv
import json
import sys
import ecommonsharvest
from fuzzywuzzy import fuzz
import os.path
import time
import strikeamatch
"""
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
    eCommonsSubset['record'] = []
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
                    eCommonsSubset['record'].append(eCommonsDict['OAI-PMH']['ListRecords']['record'][n])
                    pass
                else:
                    pass
            except KeyError:
                pass
    print("Saving eCommons roles locally as a backup.")
    with open("data/eCommonsRoles.json", 'w') as f:
        json.dump(eCommonsSubset, f)
    return(eCommonsSubset)


def matchingAlgos(string1, string2):
    matchranking = fuzz.ratio(string1, string2)
    matchranking2 = strikeamatch.compare_strings(string1, string2)
    if matchranking > 75 or matchranking2 > .7:
        print("Matching: " + string1 + " to " + string2 + " with scores: " +
              str(matchranking) + ' | ' + str(matchranking2))
    return(matchranking)


def compareECtoVIVO(VIVOppl, eCommonsDict):
    """compare eCommons to VIVO."""
    print('Now matching VIVO to eCommons')
    VIVOmatches = []
    eCommonsMatched = []
    for n in range(len(eCommonsDict['record'])):
        handle = None
        subjs = []
        record = eCommonsDict['record'][n]
        oaiID = record['header']['identifier']
        setSpecs = []
        setSpecs.append(record['header']['setSpec'])
        metadata = record['metadata']
        for m in range(len(metadata['dim:dim']['dim:field'])):
            try:
                field = metadata['dim:dim']['dim:field'][m]
                if field['@element'] == 'identifier' and field['@qualifier'] == 'uri':
                    handle = field['#text']
            except KeyError:
                pass

            try:
                field = metadata['dim:dim']['dim:field'][m]
                if field['@element'] == 'subject':
                    subjs.append(field['#text'])
            except KeyError:
                pass
        for m in range(len(metadata['dim:dim']['dim:field'])):
            try:
                field = metadata['dim:dim']['dim:field'][m]
                if field['@element'] == 'contributor' and field['@qualifier'] in roles:
                    for uri, label in VIVOppl.items():
                        matchranking = matchingAlgos(label, field['#text'])
                        if matchranking > 90:
                            VIVOmatchrow = [uri, label, handle]
                            VIVOmatchrow.append(field['@qualifier'])
                            VIVOmatchrow.append(field['#text'])
                            VIVOmatchrow.append(subjs)
                            ECmatchrow = []
                            ECmatchrow.append(handle)
                            ECmatchrow.append(setSpecs)
                            ECmatchrow.append(oaiID)
                            ECmatchrow.append(subjs)
                            ECmatchrow.append(field['@element'])
                            ECmatchrow.append(field['@qualifier'])
                            ECmatchrow.append(uri)
                            if VIVOmatchrow not in VIVOmatches:
                                VIVOmatches.append(VIVOmatchrow)
                            if ECmatchrow not in eCommonsMatched:
                                eCommonsMatched.append(ECmatchrow)
            except KeyError:
                print('KEY ERROR AT ' + str(oaiID))
                pass
    return(VIVOmatches, eCommonsMatched)


def writeVIVOtoCsv(dictionary):
    """Write the matching outputs to CSV for reingest."""
    with open('data/VIVOmatched.csv', 'w') as f:
        w = csv.writer(f)
        header = ['uri', 'label', 'EChandle', 'element qualifier', 'EClabel',
                  'EC Subjects']
        w.writerow(header)
        w.writerows(dictionary)


def writeECtoCsv(dictionary):
    """Write the matching outputs to JSON for now. To be fixed."""
    with open('data/ECmatched.csv', 'w') as f:
        w = csv.writer(f)
        header = ['handle', 'set', 'oaiID', 'subjects', 'element', 'qualifier',
                  'VIVO URI']
        w.writerow(header)
        w.writerows(dictionary)


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
        print("Please provide a URI or list of URIs as a text file")
        exit()


if __name__ == "__main__":
    main()
