"""Match handles from eCommons XML to Catalog Bib Records. Return JSON."""
import pymarc
import eCommonsVIVO as ECV


def matchMARCtoEC(matches, marcfile):
    """Get Catalog BibIDs (001) for records matched to eCommons."""
    with open(marcfile, 'rb') as data:
        reader = pymarc.MARCReader(data)
        for record in reader:
            bibID = record['001'].value()
            if record['856']:
                bibURL = record['856']['u']
                for handle in matches.keys():
                    if handle.strip() == bibURL.strip():
                        matches[handle] = bibID
        return(matches)


def getEChandles(eCommonsDict, matchesDict):
    """Grab just the handles from eCommons, load into response dict."""
    print('Pulling handles from eCommons...')
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
                        matchesDict[field['#text']] = ''
    return(matchesDict)


def main():
    """Main function: run MARC <=> eCommons matching."""
    marc = 'data/marc.mrc'
    matches = {}
    # First, retrieve eCommons XML.
    ECV.retrieveECommons()
    eCommonsAll = ECV.eCommonsXMLtoDict("data/eCommons.xml")
    # Next, pull all all the handles, load as keys into dict.
    matches = getEChandles(eCommonsAll, matches)
    # Now, run through handles, match with MARC 856, grab bib if match.
    matches = matchMARCtoEC(matches, marc)
    return(matches)


if __name__ == "__main__":
    main()
