"""Grab eCommons XML."""
import urllib.request
import urllib.error
import zlib
import time
import re
import xml.dom.pulldom
import xml.dom.minidom
import codecs

nDataBytes, nRawBytes, nRecoveries, maxRecoveries = 0, 0, 0, 3


def getFile(link, command, verbose=1, sleepTime=0):
    """getFile function taken from MetadataBreakers."""
    global nRecoveries, nDataBytes, nRawBytes
    if sleepTime:
        time.sleep(sleepTime)
    remoteAddr = link + '?verb=%s' % command
    if verbose:
        print("\r", "getFile ...'%s'" % remoteAddr[-90:])
    try:
        remoteData = urllib.request.urlopen(remoteAddr).read().decode('utf-8')
    except urllib.error.HTTPError as exValue:
        if exValue.code == 503:
            retryWait = int(exValue.hdrs.get("Retry-After", "-1"))
            if retryWait < 0:
                return None
            print('Waiting %d seconds' % retryWait)
            return getFile(link, command, 0, retryWait)
        print(exValue)
        if nRecoveries < maxRecoveries:
            nRecoveries += 1
            return getFile(link, command, 1, 60)
        return
    nRawBytes += len(remoteData)
    try:
        remoteData = zlib.decompressobj().decompress(remoteData)
    except:
        pass
    nDataBytes += len(remoteData)
    mo = re.search(u'<error *code=\"([^"]*)">(.*)</error>', remoteData)
    if mo:
        print("OAIERROR: code=%s '%s'" % (mo.group(1), mo.group(2)))
    else:
        return remoteData


def main():
    """Get info for grabbing eCommons XML, write to file."""
    link = 'http://ecommons.cornell.edu/dspace-oai/request'
    print("Writing records from eCommons")
    verbOpts = '&metadataPrefix=dim'

    ofile = codecs.lookup('utf-8')[-1](open("data/eCommons.xml", 'wb'))

    ofile.write('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH><ListRecords>')

    data = getFile(link, 'ListRecords' + verbOpts)
    recordCount = 0

    while data:
        events = xml.dom.pulldom.parseString(data)
        for (event, node) in events:
            if event == "START_ELEMENT" and node.tagName == 'record':
                events.expandNode(node)
                node.writexml(ofile)
                recordCount += 1
        more = re.search('<resumptionToken[^>]*>(.*)</resumptionToken>', data)
        if not more:
            break
        data = getFile(link, "ListRecords&resumptionToken=%s" % more.group(1))

    ofile.write('\n</ListRecords></OAI-PMH>\n'), ofile.close()
    print("Wrote out %d records" % recordCount)


if __name__ == "__main__":
    main()
