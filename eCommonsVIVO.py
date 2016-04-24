"""Match people from VIVO department to eCommons roles."""
import rdflib
from rdflib.namespace import RDF, FOAF
import xmltodict
import csv
import json
import ecommonsharvest
from fuzzywuzzy import fuzz
import os.path
import time
import strikeamatch
import argparse
import re
import pymarc
"""
Validate matches = specializations?
"""
VIVO = rdflib.Namespace("http://vivoweb.org/ontology/core#")
hr = rdflib.Namespace("http://vivo.cornell.edu/ns/hr/0.9/hr.owl#")
ns = {'http://www.openarchives.org/OAI/2.0/': None,
      'http://www.dspace.org/xmlns/dspace/dim': 'dim'}
roles = ['chair', 'committeeMember', 'coChair', 'advisor']
midinit_re = re.compile('([A-Za-z]+, *[A-Za-z]+ {1})([A-Za-z]){1}\.*$')


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
        eCommonsDictBibs = eCommonsAddBibs(eCommonsDict)
    # return(eCommonsDictBibs)


def matchMARCtoEC(handle):
    """Get Catalog BibIDs (001) for records matched to eCommons."""
    with open('data/ETDsutf8.mrc', 'rb') as data:
        reader = pymarc.MARCReader(data)
        for record in reader:
            bibID = record['001'].value()
            bibURL = record['856']['u']
            if handle.strip() == bibURL.strip():
                print('Bib <=> EC match: ' + str(bibID) + ' = ' + handle)
                return(bibID)
            else:
                return(None)


def eCommonsAddBibs(eCommonsDict):
    """Add matched Catalog Bib Ids to eCommons Dictionary."""
    print('Matching Catalog bibs to eCommons records...')
    for n in range(len(eCommonsDict['OAI-PMH']['ListRecords']['record'])):
        record = eCommonsDict['OAI-PMH']['ListRecords']['record'][n]
        if 'metadata' in record.keys():
            metadata = record['metadata']
            for m in range(len(metadata['dim:dim']['dim:field'])):
                field = metadata['dim:dim']['dim:field'][m]
                if '@qualifier' in field.keys():
                    elem = field['@element']
                    qualifier = field['@qualifier']
                    if elem == 'identifier' and qualifier == 'uri':
                        bibID = matchMARCtoEC(field['#text'])
                        if bibID:
                            newfield = {}
                            newfield['#text'] = bibID
                            newfield['@element'] = 'identifier'
                            newfield['@mdschema'] = 'dc'
                            newfield['@qualifier'] = 'bibID'
                            metadata['dim:dim']['dim:field'].append(newfield)
    print('Done matching bib IDs to eCommons records for this subset.')
    #return(eCommonsDict)


def eCommonsRoles(eCommonsDict):
    """Grab eCommons (DSpace) records only with wanted roles."""
    eCommonsSubset = {}
    eCommonsSubset['record'] = []
    print("Getting only eCommons records with chosen roles.")
    for n in range(len(eCommonsDict['OAI-PMH']['ListRecords']['record'])):
        try:
            record = eCommonsDict['OAI-PMH']['ListRecords']['record'][n]
            metadata = record['metadata']
        except KeyError:
            pass
        for m in range(len(metadata['dim:dim']['dim:field'])):
            field = metadata['dim:dim']['dim:field'][m]
            try:
                elem = field['@element']
                if elem == 'contributor' and field['@qualifier'] in roles:
                    eCommonsSubset['record'].append(record)
                    break
                else:
                    pass
            except KeyError:
                pass
    print("Saving eCommons roles locally as a backup.")
    with open("data/eCommonsRoles.json", 'w') as f:
        json.dump(eCommonsSubset, f)
    return(eCommonsSubset)


def matchingAlgos(string1, string2):
    """using variety of matching algorithms to get results."""
    matchranking1 = fuzz.ratio(string1, string2)
    matchranking2 = strikeamatch.compare_strings(string1, string2) * 100
    # verify match isn't based just on everything except middle inits
    m1 = midinit_re.match(string1)
    m2 = midinit_re.match(string2)
    if m1 and m2:
        if m1.group(1) == m2.group(1) and m1.group(2) != m2.group(2):
            matchranking1 -= 10
            matchranking2 -= 10
            print('TESTING MID INIT MISMATCHING DECREASE')
            print("Matching: " + string1 + " to " + string2 + " scores: " +
                  str(matchranking1) + ' | ' + str(matchranking2))
    # proceed with grabbing best ranking match
    if matchranking1 > 85 or matchranking2 > 80:
        print("Matching: " + string1 + " to " + string2 + " scores: " +
              str(matchranking1) + ' | ' + str(matchranking2))
    matchranking = max(matchranking1, matchranking2)
    return(matchranking)


def compareECtoVIVO(VIVOppl, eCommonsDict):
    """compare eCommons to VIVO."""
    print('Now matching VIVO to eCommons')
    VIVOmatches = []
    eCommonsMatched = []
    for n in range(len(eCommonsDict['record'])):
        handle = None
        subjs = []
        bibID = None
        record = eCommonsDict['record'][n]
        oaiID = record['header']['identifier']
        setSpecs = []
        setSpecs.append(record['header']['setSpec'])
        metadata = record['metadata']
        for m in range(len(metadata['dim:dim']['dim:field'])):
            try:
                field = metadata['dim:dim']['dim:field'][m]
                elem = field['@element']
                if elem == 'identifier' and field['@qualifier'] == 'uri':
                    handle = field['#text']
            except KeyError:
                pass
            try:
                field = metadata['dim:dim']['dim:field'][m]
                if field['@element'] == 'subject':
                    subjs.append(field['#text'])
            except KeyError:
                pass
            try:
                field = metadata['dim:dim']['dim:field'][m]
                elem = field['@element']
                if elem == 'identifier' and field['@qualifier'] == 'bibID':
                    bibID = field['#text']
            except KeyError:
                pass
        for m in range(len(metadata['dim:dim']['dim:field'])):
            try:
                field = metadata['dim:dim']['dim:field'][m]
                elem = field['@element']
                if elem == 'contributor' and field['@qualifier'] in roles:
                    for uri, label in VIVOppl.items():
                        matchranking = matchingAlgos(label, field['#text'])
                        if matchranking > 90:
                            VIVOmatchrow = [uri, label, handle]
                            VIVOmatchrow.append(field['@qualifier'])
                            VIVOmatchrow.append(field['#text'])
                            VIVOmatchrow.append(subjs)
                            VIVOmatchrow.append(bibID)
                            ECmatchrow = []
                            ECmatchrow.append(handle)
                            ECmatchrow.append(setSpecs)
                            ECmatchrow.append(oaiID)
                            ECmatchrow.append(subjs)
                            ECmatchrow.append(field['@element'])
                            ECmatchrow.append(field['@qualifier'])
                            ECmatchrow.append(uri)
                            ECmatchrow.append(bibID)
                            if VIVOmatchrow not in VIVOmatches:
                                VIVOmatches.append(VIVOmatchrow)
                            if ECmatchrow not in eCommonsMatched:
                                eCommonsMatched.append(ECmatchrow)
            except KeyError:
                print('KEY ERROR AT ' + str(oaiID))
                pass
    return(VIVOmatches, eCommonsMatched)


def writeVIVOtoCsv(matches):
    """Write the matching outputs to CSV for sharing w/VIVO team."""
    with open('data/VIVOmatched.csv', 'w') as f:
        w = csv.writer(f)
        header = ['uri', 'label', 'EChandle', 'element qualifier', 'EClabel',
                  'EC Subjects', 'Bib ID']
        w.writerow(header)
        w.writerows(matches)


def writeECtoCsv(matches):
    """Write the matching outputs to CSV for reingest."""
    with open('data/ECmatched.csv', 'w') as f:
        w = csv.writer(f)
        header = ['handle', 'set', 'oaiID', 'subjects', 'element', 'qualifier',
                  'VIVO URI', 'Bib ID']
        w.writerow(header)
        w.writerows(matches)


def main():
    """Main function: run people matching."""
    parser = argparse.ArgumentParser(usage='python %(prog)s [options]')
    parser.add_argument("-u", "--uri", dest="uri", help="1 uri")
    parser.add_argument("-f", "--file", dest="file", help="file of URIs")

    args = parser.parse_args()

    if not args.uri and not args.file:
        parser.print_help()
        parser.exit()

    if args.uri:
        # grab VIVO data
        VIVOppl = getVIVOppl(args.uri)
    elif args.file:
        with open(args.file) as f:
            URIs = f.readlines()
        VIVOppl = getVIVOppl(URIs)
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


if __name__ == "__main__":
    main()
