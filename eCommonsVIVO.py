import rdflib
import time
import xmltodict
import csv

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

