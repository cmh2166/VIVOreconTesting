"""Match people from VIVO department to eCommons roles."""
import rdflib
from rdflib.namespace import RDF, FOAF
import xmltodict
import csv
import sys
import ecommonsharvest
import fuzzywuzzy
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


def getVIVOppl(deptURI):
    """Generate VIVO Graph containing people in that dept, return people."""
    VIVOgraph = rdflib.Graph()
    print("Getting VIVO data...")
    try:
        if type(deptURI) is str:
            VIVOgraph.parse(deptURI)
        elif type(deptURI) is list:
            for URI in deptURI:
                VIVOgraph.parse(URI)
    except Exception as e:
        print("Error parsing VIVO URIS: %s" % e)
        exit()

    print("getting VIVO units data...")
    for unit in VIVOgraph.objects(None, VIVO.relatedBy):
        VIVOgraph.parse(unit)
    print("getting VIVO positions data...")
    for pos in VIVOgraph.subjects(hr.positionInUnit, None):
        VIVOgraph.parse(pos)
    people = {}
    print("getting VIVO people data...")
    for person in VIVOgraph.subjects(RDF.type, FOAF.Person):
        # do further testing to ensure we grab only employees
        label = VIVOgraph.preferredLabel(person)[0][1].toPython()
        people[person.toPython()] = label
    print("got VIVO graph successfully.")
    return(people)


def eCommonsXMLtoDict(eCommonsXML):
    """Translate eCommons XML to dict."""
    with open(eCommonsXML) as fd:
        eCommonsDict = xmltodict.parse(fd.read(), namespaces=ns)
    return(eCommonsDict)


def eCommonsRoles(eCommonsDict):
    """Grab eCommons records only with wanted roles."""
    eCommonsSubset = {}
    roles = ['chair', 'committeeMember', 'coChair', 'advisor']
    for n in range(len(eCommonsDict['OAI-PMH']['ListRecords']['record'])):
        try:
            metadata = eCommonsDict['OAI-PMH']['ListRecords']['record'][n]['metadata']
        except IndexError:
            pass
        for m in range(len(metadata['dim:dim']['dim:field'])):
            field = metadata['dim:dim']['dim:field'][m]
            if field['@element'] == 'contributor' and field['@qualifier'] in roles:
                eCommonsSubset.update(eCommonsDict['OAI-PMH']['ListRecords']['record'][n])
                pass
            else:
                pass
    return(eCommonsSubset)


def compareECtoVIVO(VIVOppl, eCommonsDict):
    """compare eCommons to VIVO.""""
    


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
        ecommonsharvest.main()
        eCommonsAll = eCommonsXMLtoDict("data/eCommons.xml")
        # only review records that have roles to be queried
        eCommonsSubset = eCommonsRoles(eCommonsAll)
        #
    else:
        print("Please provide a URI or list of URIs")
        exit()


if __name__ == "__main__":
    main()
